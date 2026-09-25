"""Попытка FMC: старт отсчёта, черновик, заморозка и сдача решения.

Адреса: /api/series/<id>/fmc/…. Серия FMC начинается общим стартом серии
(series.py), а каждая попытка — своим стартом со своим часом. Решение
проверяет клиент, сервер сохраняет его результат вместе с текстом решения.
Правила — раздел «FMC» CLAUDE.md.
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
from .permissions import get_or_404
from .scoring import VersionConflict, save_attempt
from .series import (
    find_fmc_attempt, fmc_deadline, require_live, serialize_my_series,
)

fmc_bp = Blueprint("fmc", __name__)

MAX_SOLUTION_LENGTH = 1000
# Ходы, которые можно набрать на клавиатуре FMC: грани, широкие повороты, перехваты.
MOVE_RE = re.compile(r"(?:[RLUDFB]w?|[xyz])['2]?")
# Решение длиннее — DNF по регламенту WCA. Сам DNF ставит клиент при проверке.
MAX_MOVES = 80


def get_my_fmc_series(series_id):
    series = get_or_404(Series, series_id, "Серия не найдена")
    if series.user_id != current_user.id:
        raise ApiError(403, "forbidden", "Это чужая серия")
    if not is_fmc(series.meetup_event.event_id):
        raise ApiError(409, "not_fmc", "Это не серия FMC")
    require_live(series.meetup_event.meetup)
    if series.status == SeriesStatus.COMPLETED:
        raise ApiError(409, "series_completed", "Серия уже завершена")
    return series


def check_number(series, data):
    """Номер попытки из запроса: только следующая несданная попытка серии."""
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
    """Решение из запроса: ходы через один пробел."""
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
    """Старт попытки: с этого момента идёт час и выдаётся скрамбл.

    Повторный старт возвращает уже начатую попытку (двойное нажатие).
    """
    series = get_my_fmc_series(series_id)
    number = check_number(series, json_body())
    if find_fmc_attempt(series, number) is None:
        series.fmc_attempts.append(FmcAttempt(attempt_number=number, started_at=utcnow()))
        try:
            db.session.commit()
        except IntegrityError:
            # Попытку успел начать параллельный запрос.
            db.session.rollback()
            series = db.session.get(Series, series_id)
    return series_response(series)


@fmc_bp.put("/series/<int:series_id>/fmc/draft")
@login_required
def save_draft(series_id):
    """Черновик решения. После дедлайна и при заморозке не принимается."""
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
    """Первый шаг сдачи: замораживает текст решения и время сдачи.

    Заморозка после дедлайна (плохая сеть) всё равно фиксирует текст, но
    попытка сразу сохраняется как DNF — снять его может организатор.
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
    """«Вернуться к решению»: снимает заморозку, пока время не вышло."""
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
    """Второй шаг сдачи: результат, посчитанный клиентом.

    Решение — замороженный текст, а если время вышло без сдачи — последний
    черновик. Клиент присылает текст, который проверял: если он не совпадает
    с сохранённым, сохранение отклоняется и клиент перечитывает серию.
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
    """Ходы, штраф и версия. У DNF ходов нет, +2 в FMC не бывает."""
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
    """save_attempt с фиксацией; при конфликте версий — 409 со свежей серией."""
    series_id = series.id
    try:
        save_attempt(series, number, value, penalty, version, current_user, **kwargs)
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        conflict = VersionConflict()
        conflict.extra = {"series": serialize_my_series(db.session.get(Series, series_id))}
        raise conflict
