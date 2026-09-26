"""FMC attempt: countdown start, draft, freezing and submitting the solution.

Routes: /api/series/<id>/fmc/…. An FMC series begins with the common series start
(series.py), and each attempt has its own start and its own hour. The solution
is checked by the client; the server stores its result along with the solution text.
Rules: "FMC" in docs/ARCHITECTURE.md.
"""

import re

from flask import Blueprint
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from .errors import ApiError
from .events import is_fmc
from .extensions import db
from .forms import get_str, is_int, json_body
from .meetups import iso_utc
from .models import FmcAttempt, Penalty, Series, SeriesStatus, utcnow
from .permissions import get_or_404, require_not_banned
from .scoring import VersionConflict, save_attempt
from .series import (
    find_fmc_attempt, fmc_deadline, require_live, serialize_my_series,
)

fmc_bp = Blueprint("fmc", __name__)

MAX_SOLUTION_LENGTH = 1000
# Moves available on the FMC keyboard: faces, wide turns, rotations.
MOVE_RE = re.compile(r"(?:[RLUDFB]w?|[xyz])['2]?")
# A longer solution is DNF under the WCA regulations. The client sets the DNF itself when checking.
MAX_MOVES = 80


def get_my_fmc_series(series_id):
    series = get_or_404(Series, series_id, "Серия не найдена")
    if series.user_id != current_user.id:
        raise ApiError(403, "forbidden", "Это чужая серия")
    if not is_fmc(series.meetup_event.event_id):
        raise ApiError(409, "not_fmc", "Это не серия FMC")
    require_live(series.meetup_event.meetup)
    require_not_banned(series.meetup_event.meetup.club_id)
    if series.status == SeriesStatus.COMPLETED:
        raise ApiError(409, "series_completed", "Серия уже завершена")
    return series


def check_number(series, data):
    """Attempt number from the request: only the next unsubmitted attempt of the series."""
    number = data.get("attempt_number")
    if not is_int(number):
        raise ApiError(422, "invalid_attempt", "Некорректный номер попытки")
    if number != len(series.attempts) + 1:
        raise ApiError(
            409, "wrong_attempt_number", "Эта попытка уже сдана или ещё не началась",
            extra={"series": serialize_my_series(series)},
        )
    return number


def get_started(series, number):
    fmc_attempt = find_fmc_attempt(series, number)
    if fmc_attempt is None:
        raise ApiError(409, "not_started", "Попытка ещё не начата")
    return fmc_attempt


def parse_solution(data):
    """Solution from the request: moves separated by single spaces."""
    solution = get_str(data, "solution")
    moves = solution.split()
    if len(solution) > MAX_SOLUTION_LENGTH or not all(MOVE_RE.fullmatch(m) for m in moves):
        raise ApiError(422, "invalid_solution", "Некорректная запись решения")
    return " ".join(moves)


def series_response(series):
    return {"series": serialize_my_series(series)}


@fmc_bp.post("/series/<int:series_id>/fmc/start")
@login_required
def start_attempt(series_id):
    """Attempt start: from this moment the hour runs and the scramble is given out.

    A repeated start returns the already started attempt (double tap).
    """
    series = get_my_fmc_series(series_id)
    number = check_number(series, json_body())
    if find_fmc_attempt(series, number) is None:
        series.fmc_attempts.append(FmcAttempt(attempt_number=number, started_at=utcnow()))
        try:
            db.session.commit()
        except IntegrityError:
            # A concurrent request has already started the attempt.
            db.session.rollback()
            series = db.session.get(Series, series_id)
    return series_response(series)


@fmc_bp.put("/series/<int:series_id>/fmc/draft")
@login_required
def save_draft(series_id):
    """Solution draft. Not accepted after the deadline or while frozen."""
    series = get_my_fmc_series(series_id)
    data = json_body()
    fmc_attempt = get_started(series, check_number(series, data))
    solution = parse_solution(data)
    if fmc_attempt.frozen_at is not None:
        raise ApiError(409, "frozen", "Решение уже сдаётся")
    now = utcnow()
    if now >= fmc_deadline(fmc_attempt):
        raise ApiError(409, "time_over", "Время вышло")

    fmc_attempt.draft = solution
    fmc_attempt.draft_saved_at = now
    db.session.commit()
    return {"draft_saved_at": iso_utc(now)}


@fmc_bp.post("/series/<int:series_id>/fmc/freeze")
@login_required
def freeze(series_id):
    """First submission step: freezes the solution text and the submission time.

    Freezing after the deadline (bad network) still records the text, but
    the attempt is saved as DNF right away; the organizer can remove it.
    """
    series = get_my_fmc_series(series_id)
    data = json_body()
    number = check_number(series, data)
    fmc_attempt = get_started(series, number)
    if fmc_attempt.frozen_at is not None:
        return series_response(series)
    solution = parse_solution(data)

    now = utcnow()
    fmc_attempt.frozen_solution = solution
    fmc_attempt.frozen_at = now
    if now < fmc_deadline(fmc_attempt):
        fmc_attempt.draft = solution
        fmc_attempt.draft_saved_at = now
        db.session.commit()
        return series_response(series)

    save_or_conflict(
        series, number, None, Penalty.DNF, series.version,
        solution=solution, submitted_at=now,
    )
    return series_response(series)


@fmc_bp.delete("/series/<int:series_id>/fmc/freeze")
@login_required
def unfreeze(series_id):
    """Back to solution: removes the freeze while time is not over."""
    series = get_my_fmc_series(series_id)
    fmc_attempt = get_started(series, check_number(series, json_body()))
    if utcnow() >= fmc_deadline(fmc_attempt):
        raise ApiError(409, "time_over", "Время вышло")
    fmc_attempt.frozen_solution = None
    fmc_attempt.frozen_at = None
    db.session.commit()
    return series_response(series)


@fmc_bp.post("/series/<int:series_id>/fmc/result")
@login_required
def submit_result(series_id):
    """Second submission step: the result computed by the client.

    The solution is the frozen text or, if time ran out without submission, the last
    draft. The client sends the text it checked: if it does not match the stored
    one, the save is rejected and the client reloads the series.
    """
    series = get_my_fmc_series(series_id)
    data = json_body()
    number = check_number(series, data)
    fmc_attempt = get_started(series, number)
    value, penalty, version = parse_result(data)

    if fmc_attempt.frozen_at is not None:
        solution, submitted_at = fmc_attempt.frozen_solution, fmc_attempt.frozen_at
    elif utcnow() >= fmc_deadline(fmc_attempt):
        solution, submitted_at = fmc_attempt.draft, fmc_deadline(fmc_attempt)
    else:
        raise ApiError(409, "not_frozen", "Решение ещё не сдано")
    if get_str(data, "solution") != solution:
        raise ApiError(
            409, "solution_changed", "Решение успело измениться, данные обновлены",
            extra={"series": serialize_my_series(series)},
        )

    save_or_conflict(
        series, number, value, penalty, version,
        solution=solution, submitted_at=submitted_at,
    )
    return series_response(series), 201


def parse_result(data):
    """Moves, penalty and version. DNF has no moves; FMC never has +2."""
    value = data.get("value")
    penalty = get_str(data, "penalty")
    version = data.get("version")
    if not is_int(version):
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")
    if penalty == Penalty.DNF and value is None:
        return None, Penalty.DNF, version
    if penalty == Penalty.NONE and is_int(value) and 0 < value <= MAX_MOVES:
        return value, Penalty.NONE, version
    raise ApiError(422, "invalid_attempt", "Некорректный результат попытки")


def save_or_conflict(series, number, value, penalty, version, **kwargs):
    """save_attempt with commit; on a version conflict, 409 with the fresh series."""
    series_id = series.id
    try:
        save_attempt(series, number, value, penalty, version, current_user, **kwargs)
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        conflict = VersionConflict()
        conflict.extra = {"series": serialize_my_series(db.session.get(Series, series_id))}
        raise conflict
