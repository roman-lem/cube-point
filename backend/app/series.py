"""Серии и попытки участника, таблица результатов дисциплины.

Адреса: /api/meetups/<id>/events/<event_id>/…, /api/series/<id>/attempts,
/api/me/active, /api/me/series. Правила — в разделах «Встречи», «Дисциплины и форматы»
и «Одновременная запись» CLAUDE.md.
"""

from flask import Blueprint
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from .errors import ApiError
from .events import FMC_TIME_LIMIT, is_fmc
from .extensions import db
from .forms import get_str, is_int, json_body
from .meetups import get_meetup, iso_utc
from .models import (
    Disqualification, Meetup, MeetupEvent, MeetupParticipant, MeetupStatus,
    ParticipantStatus, Penalty, Series, SeriesStatus, utcnow,
)
from .permissions import get_or_404
from .results import ATTEMPTS_COUNT
from .scoring import VersionConflict, event_table, save_attempt, serialize_attempt

series_bp = Blueprint("series", __name__)

# Меньше часа в сотых долях секунды.
MAX_VALUE = 360_000
# DNS участник не ставит: его ставит завершение встречи или организатор.
PARTICIPANT_PENALTIES = {p.value for p in (Penalty.NONE, Penalty.PLUS2, Penalty.DNF)}


def get_meetup_event(meetup, event_id):
    meetup_event = db.session.scalar(db.select(MeetupEvent).where(
        MeetupEvent.meetup_id == meetup.id, MeetupEvent.event_id == event_id,
    ))
    if meetup_event is None:
        raise ApiError(404, "not_found", "Дисциплины нет на этой встрече")
    return meetup_event


def require_live(meetup):
    if meetup.status != MeetupStatus.LIVE:
        raise ApiError(409, "meetup_not_live", "Встреча сейчас не идёт")


def serialize_attempts(series):
    result = []
    for a in series.attempts:
        item = {"number": a.attempt_number, **serialize_attempt(a)}
        if a.solution is not None:
            item["solution"] = a.solution
        result.append(item)
    return result


def fmc_deadline(fmc_attempt):
    return fmc_attempt.started_at + FMC_TIME_LIMIT


def serialize_fmc(fmc_attempt):
    """Состояние начатой попытки FMC. server_now — чтобы клиент поправил свои часы."""
    return {
        "started_at": iso_utc(fmc_attempt.started_at),
        "deadline": iso_utc(fmc_deadline(fmc_attempt)),
        "server_now": iso_utc(utcnow()),
        "draft": fmc_attempt.draft,
        "frozen_solution": fmc_attempt.frozen_solution,
        "frozen_at": iso_utc(fmc_attempt.frozen_at),
    }


def find_fmc_attempt(series, number):
    return next((f for f in series.fmc_attempts if f.attempt_number == number), None)


def serialize_my_series(series):
    """Серия для её владельца: скрамбл только у следующей попытки.

    В FMC скрамбл есть только после старта попытки, а next_attempt.fmc —
    состояние начатой попытки (None, пока она не начата).
    """
    meetup_event = series.meetup_event
    next_attempt = None
    if series.status == SeriesStatus.IN_PROGRESS:
        number = len(series.attempts) + 1
        scramble = next(
            s for s in meetup_event.scrambles if s.attempt_number == number
        )
        next_attempt = {"number": number, "scramble": scramble.scramble}
        if is_fmc(meetup_event.event_id):
            fmc_attempt = find_fmc_attempt(series, number)
            next_attempt["fmc"] = serialize_fmc(fmc_attempt) if fmc_attempt else None
            if fmc_attempt is None:
                next_attempt["scramble"] = None
    return {
        "id": series.id,
        "meetup_id": meetup_event.meetup_id,
        "event_id": meetup_event.event_id,
        "format": meetup_event.format.value,
        "status": series.status.value,
        "version": series.version,
        "attempts": serialize_attempts(series),
        "best": series.best,
        "average": series.average,
        "next_attempt": next_attempt,
    }


def find_series(meetup_event, user_id):
    return db.session.scalar(db.select(Series).where(
        Series.meetup_event_id == meetup_event.id, Series.user_id == user_id,
    ))


# Серия участника

@series_bp.post("/meetups/<int:meetup_id>/events/<event_id>/series")
@login_required
def start_series(meetup_id, event_id):
    meetup = get_meetup(meetup_id)
    meetup_event = get_meetup_event(meetup, event_id)
    require_live(meetup)

    participant = db.session.get(MeetupParticipant, (meetup.id, current_user.id))
    if participant is None or participant.status != ParticipantStatus.APPROVED:
        raise ApiError(403, "not_approved", "Организатор ещё не подтвердил участие")
    if db.session.scalar(db.select(Disqualification.id).where(
        Disqualification.meetup_id == meetup.id,
        Disqualification.user_id == current_user.id,
    )):
        raise ApiError(403, "disqualified", "Вы дисквалифицированы на этой встрече")
    if find_series(meetup_event, current_user.id):
        raise ApiError(409, "series_exists", "Серия в этой дисциплине уже начата")

    series = Series(meetup_event=meetup_event, user_id=current_user.id)
    db.session.add(series)
    try:
        db.session.commit()
    except IntegrityError:
        # Серию успел создать параллельный запрос (двойное нажатие).
        db.session.rollback()
        raise ApiError(409, "series_exists", "Серия в этой дисциплине уже начата")
    return {"series": serialize_my_series(series)}, 201


@series_bp.get("/meetups/<int:meetup_id>/events/<event_id>/series/me")
@login_required
def my_series(meetup_id, event_id):
    meetup_event = get_meetup_event(get_meetup(meetup_id), event_id)
    series = find_series(meetup_event, current_user.id)
    if series is None:
        raise ApiError(404, "not_found", "Серия не начата")
    return {"series": serialize_my_series(series)}


@series_bp.post("/series/<int:series_id>/attempts")
@login_required
def submit_attempt(series_id):
    series = get_or_404(Series, series_id, "Серия не найдена")
    if series.user_id != current_user.id:
        raise ApiError(403, "forbidden", "Это чужая серия")
    require_live(series.meetup_event.meetup)
    if series.status == SeriesStatus.COMPLETED:
        raise ApiError(409, "series_completed", "Серия уже завершена")
    if is_fmc(series.meetup_event.event_id):
        raise ApiError(409, "fmc_series", "Попытки FMC сдаются с экрана FMC")

    data = json_body()
    number, value, penalty, version = parse_attempt(data)
    # Попытки строго по порядку. Сохранённую попытку участник не меняет.
    if number != len(series.attempts) + 1:
        raise ApiError(
            409, "wrong_attempt_number", "Эта попытка уже сохранена или ещё не началась",
            extra={"series": serialize_my_series(series)},
        )

    try:
        save_attempt(series, number, value, penalty, version, current_user)
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        series = db.session.get(Series, series_id)
        conflict = VersionConflict()
        conflict.extra = {"series": serialize_my_series(series)}
        raise conflict
    return {"series": serialize_my_series(series)}, 201


def parse_attempt(data):
    """Номер, время, штраф и версия из запроса участника. Ошибка — 422 без полей формы."""
    number = data.get("attempt_number")
    version = data.get("version")
    if not is_int(number) or not is_int(version):
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")
    value, penalty = parse_value(data, PARTICIPANT_PENALTIES)
    return number, value, penalty, version


def parse_value(data, penalties, max_value=MAX_VALUE):
    """Значение и штраф попытки из запроса: время (или ходы) меньше max_value.

    При DNF и DNS значение необязательно: время сохранится, если штраф снимут.
    """
    value = data.get("value")
    penalty = get_str(data, "penalty")
    if penalty not in penalties:
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")
    penalty = Penalty(penalty)
    if value is None and penalty in (Penalty.DNF, Penalty.DNS):
        return None, penalty
    if not is_int(value) or not 0 < value < max_value:
        raise ApiError(422, "invalid_attempt", "Некорректное значение попытки")
    return value, penalty


# Таблица дисциплины

@series_bp.get("/meetups/<int:meetup_id>/events/<event_id>/results")
def event_results(meetup_id, event_id):
    """Таблица результатов дисциплины. Открыта всем, в том числе гостям."""
    meetup = get_meetup(meetup_id)
    meetup_event = get_meetup_event(meetup, event_id)
    count = ATTEMPTS_COUNT[meetup_event.format.value]
    rows = []
    for row in event_table(meetup_event):
        series = row["series"]
        attempts = [None] * count
        for attempt in series.attempts:
            attempts[attempt.attempt_number - 1] = serialize_attempt(attempt)
        rows.append({
            "place": row["place"],
            "user": {"id": series.user.id, "display_name": series.user.display_name},
            "status": series.status.value,
            "attempts": attempts,
            "best": series.best,
            "average": series.average,
            "marks": row["marks"],
        })
    return {
        "meetup": {
            "id": meetup.id,
            "date": meetup.date.isoformat(),
            "status": meetup.status.value,
            "club": {
                "id": meetup.club.id, "name": meetup.club.name,
                "timezone": meetup.club.timezone,
            },
        },
        "event": {"event_id": meetup_event.event_id, "format": meetup_event.format.value},
        "rows": rows,
    }


# Активные встречи текущего пользователя

@series_bp.get("/me/active")
@login_required
def my_active_meetups():
    """Идущие встречи, где пользователь подтверждён, и его серии в дисциплинах.

    Нужны таймеру, чтобы предложить «Начать серию» или «Продолжить».
    """
    meetups = db.session.scalars(
        db.select(Meetup)
        .join(MeetupParticipant)
        .where(
            Meetup.status == MeetupStatus.LIVE,
            MeetupParticipant.user_id == current_user.id,
            MeetupParticipant.status == ParticipantStatus.APPROVED,
        )
        .order_by(Meetup.starts_at.desc())
    ).all()
    my_series = {
        s.meetup_event_id: s
        for s in db.session.scalars(db.select(Series).where(
            Series.user_id == current_user.id,
            Series.meetup_event_id.in_(
                [e.id for m in meetups for e in m.events]
            ),
        ))
    }

    def series_summary(meetup_event):
        series = my_series.get(meetup_event.id)
        if series is None:
            return None
        return {"status": series.status.value, "attempts_done": len(series.attempts)}

    return {"meetups": [
        {
            "id": meetup.id,
            "date": meetup.date.isoformat(),
            "starts_at": iso_utc(meetup.starts_at),
            "place": meetup.place,
            "club": {"id": meetup.club.id, "name": meetup.club.name},
            "events": [
                {
                    "event_id": e.event_id,
                    "format": e.format.value,
                    "series": series_summary(e),
                }
                for e in meetup.events
            ],
        }
        for meetup in meetups
    ]}


@series_bp.get("/me/series")
@login_required
def my_live_series():
    """Серии пользователя на идущих встречах, сгруппированные по встречам.

    Нужны вкладке «Статистика»: серии в процессе и завершённые.
    """
    rows = db.session.scalars(
        db.select(Series)
        .join(MeetupEvent)
        .join(Meetup)
        .where(Series.user_id == current_user.id, Meetup.status == MeetupStatus.LIVE)
        .order_by(Meetup.starts_at.desc(), Meetup.id, MeetupEvent.id)
    ).all()

    meetups = {}
    for series in rows:
        meetup_event = series.meetup_event
        meetup = meetup_event.meetup
        if meetup.id not in meetups:
            meetups[meetup.id] = {
                "id": meetup.id,
                "date": meetup.date.isoformat(),
                "club": {
                    "id": meetup.club.id, "name": meetup.club.name,
                    "timezone": meetup.club.timezone,
                },
                "series": [],
            }
        attempts = [None] * ATTEMPTS_COUNT[meetup_event.format.value]
        for attempt in series.attempts:
            attempts[attempt.attempt_number - 1] = serialize_attempt(attempt)
        meetups[meetup.id]["series"].append({
            "id": series.id,
            "event_id": meetup_event.event_id,
            "format": meetup_event.format.value,
            "status": series.status.value,
            "attempts": attempts,
            "best": series.best,
            "average": series.average,
        })
    return {"meetups": list(meetups.values())}
