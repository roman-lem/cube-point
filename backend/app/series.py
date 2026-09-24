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
from .events import EVENTS
from .extensions import db
from .forms import get_str, json_body
from .meetups import get_meetup, iso_utc
from .models import (
    Disqualification, Meetup, MeetupEvent, MeetupParticipant, MeetupStatus,
    ParticipantStatus, Penalty, Series, SeriesStatus,
)
from .permissions import get_or_404
from .results import ATTEMPTS_COUNT
from .scoring import VersionConflict, attempt_dict, event_table, save_attempt

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
    return [
        {"number": a.attempt_number, **attempt_dict(a)} for a in series.attempts
    ]


def serialize_my_series(series):
    """Серия для её владельца: скрамбл только у следующей попытки."""
    meetup_event = series.meetup_event
    next_attempt = None
    if series.status == SeriesStatus.IN_PROGRESS:
        number = len(series.attempts) + 1
        scramble = next(
            s for s in meetup_event.scrambles if s.attempt_number == number
        )
        next_attempt = {"number": number, "scramble": scramble.scramble}
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
    # FMC сдаётся отдельным экраном с вводом решения, он появится позже.
    if EVENTS[event_id].result_type == "moves":
        raise ApiError(409, "not_supported", "Серии FMC пока недоступны")

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

    data = json_body()
    number, value, penalty, version = parse_attempt(data)
    # Попытки строго по порядку. Сохранённую попытку участник не меняет.
    if number != len(series.attempts) + 1:
        raise ApiError(
            409, "wrong_attempt_number", "Эта попытка уже сохранена или ещё не началась",
            extra={"series": serialize_my_series(series)},
        )

    try:
        save_attempt(series, number, value, Penalty(penalty), version, current_user)
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        series = db.session.get(Series, series_id)
        conflict = VersionConflict()
        conflict.extra = {"series": serialize_my_series(series)}
        raise conflict
    return {"series": serialize_my_series(series)}, 201


def parse_attempt(data):
    """Номер, время, штраф и версия из запроса. Ошибка — 422 без полей формы."""
    number = data.get("attempt_number")
    value = data.get("value")
    penalty = get_str(data, "penalty")
    version = data.get("version")

    def is_int(x):
        # bool — подкласс int в Python, его отсекаем явно.
        return isinstance(x, int) and not isinstance(x, bool)

    if not is_int(number) or not is_int(version) or penalty not in PARTICIPANT_PENALTIES:
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")
    # При DNF время необязательно: оно сохранится, если организатор снимет штраф.
    if value is None and penalty == Penalty.DNF:
        return number, None, penalty, version
    if not is_int(value) or not 0 < value < MAX_VALUE:
        raise ApiError(422, "invalid_attempt", "Некорректное время попытки")
    return number, value, penalty, version


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
            attempts[attempt.attempt_number - 1] = attempt_dict(attempt)
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
            attempts[attempt.attempt_number - 1] = attempt_dict(attempt)
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
