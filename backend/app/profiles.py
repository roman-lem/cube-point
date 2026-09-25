"""Публичные страницы: рекорды клуба и профиль участника.

Адреса: /api/clubs/<id>/records, /api/users/<id>, /api/users/<id>/meetups.
Открыты всем, в том числе гостям, поэтому о человеке отдаются только id и имя,
без логина. Правила — раздел «Рекорды» CLAUDE.md.

Результаты встреч, где человека дисквалифицировали, в профиле не показываются
и в PB не учитываются. Блокировка в клубе на профиль не влияет: прошлые
результаты и рекорды остаются, только клуб пропадает из списка клубов.
"""

from flask import Blueprint, request
from sqlalchemy.orm import selectinload

from .events import EVENTS
from .extensions import db
from .meetups import iso_utc
from .models import (
    Attempt, Club, ClubMember, ClubRecord, Disqualification, Meetup, MeetupEvent, RecordType,
    Series, User,
)
from .permissions import get_or_404
from .results import ATTEMPTS_COUNT
from .scoring import best_result, not_disqualified, serialize_attempt

profiles = Blueprint("profiles", __name__)

PAGE_SIZE = 10


def public_user(user):
    return {"id": user.id, "display_name": user.display_name}


def serialize_meetup_ref(meetup):
    return {
        "id": meetup.id,
        "date": meetup.date.isoformat(),
        "club": {"id": meetup.club.id, "name": meetup.club.name},
    }


# Рекорды клуба

@profiles.get("/clubs/<int:club_id>/records")
def club_records(club_id):
    """Рекорды клуба из кеша club_records: сингл и среднее по дисциплинам.

    Только дисциплины, где есть хотя бы один рекорд, в порядке EVENTS.
    """
    get_or_404(Club, club_id, "Клуб не найден")
    by_event = {}
    for record in db.session.scalars(
        db.select(ClubRecord)
        .where(ClubRecord.club_id == club_id)
        .options(selectinload(ClubRecord.user), selectinload(ClubRecord.series))
    ):
        event = by_event.setdefault(record.event_id, {"single": None, "average": None})
        event[record.type.value] = {
            "value": record.value,
            "user": public_user(record.user),
            "meetup": serialize_meetup_ref(record.series.meetup_event.meetup),
            "achieved_at": iso_utc(record.achieved_at),
        }
    return {
        "records": [
            {"event_id": event_id, **by_event[event_id]}
            for event_id in EVENTS if event_id in by_event
        ],
    }


# Профиль участника

def attended_meetups(user_id):
    """Условия для запроса по Meetup: у человека есть серия и он не дисквалифицирован."""
    has_series = db.select(Series.id).join(MeetupEvent).where(
        MeetupEvent.meetup_id == Meetup.id, Series.user_id == user_id,
    ).exists()
    disqualified = db.select(Disqualification.id).where(
        Disqualification.meetup_id == Meetup.id, Disqualification.user_id == user_id,
    ).exists()
    return has_series, ~disqualified


def personal_bests(user_id):
    """Лучшие результаты человека по всем клубам: {event_id: {"single": строка, "average": строка}}.

    Только дисциплины, где у него есть серии. Строка — из best_result или None,
    если удачных результатов нет.
    """
    event_ids = set(db.session.scalars(
        db.select(MeetupEvent.event_id).distinct()
        .join(Series).join(Meetup)
        .where(Series.user_id == user_id, not_disqualified())
    ))
    return {
        event_id: {
            record_type.value: best_result(event_id, record_type, Series.user_id == user_id)
            for record_type in RecordType
        }
        for event_id in EVENTS if event_id in event_ids
    }


@profiles.get("/users/<int:user_id>")
def user_profile(user_id):
    """Имя, клубы, число встреч и личные рекорды (PB) по дисциплинам."""
    user = get_or_404(User, user_id, "Участник не найден")
    clubs = db.session.scalars(
        db.select(Club).join(ClubMember)
        .where(ClubMember.user_id == user.id, ClubMember.banned_at.is_(None))
        .order_by(Club.name)
    ).all()
    meetups_count = db.session.scalar(
        db.select(db.func.count(Meetup.id)).where(*attended_meetups(user.id))
    )

    def serialize_best(row):
        if row is None:
            return None
        meetup = db.session.get(Series, row.series_id).meetup_event.meetup
        return {"value": row.value, "meetup": serialize_meetup_ref(meetup)}

    return {
        "user": public_user(user),
        "clubs": [{"id": club.id, "name": club.name} for club in clubs],
        "meetups_count": meetups_count,
        "personal_records": [
            {
                "event_id": event_id,
                "single": serialize_best(best["single"]),
                "average": serialize_best(best["average"]),
            }
            for event_id, best in personal_bests(user.id).items()
        ],
    }


@profiles.get("/users/<int:user_id>/meetups")
def user_meetups(user_id):
    """История встреч с результатами, от новых к старым, по PAGE_SIZE встреч.

    ?offset= — сколько встреч уже загружено. Отметки PB и LR — только актуальные рекорды.
    """
    user = get_or_404(User, user_id, "Участник не найден")
    offset = max(request.args.get("offset", 0, type=int), 0)
    meetups = db.session.scalars(
        db.select(Meetup)
        .where(*attended_meetups(user.id))
        .order_by(Meetup.date.desc(), Meetup.starts_at.desc(), Meetup.id.desc())
        .offset(offset)
        .limit(PAGE_SIZE + 1)
    ).all()
    has_more = len(meetups) > PAGE_SIZE
    meetups = meetups[:PAGE_SIZE]

    series_list = db.session.scalars(
        db.select(Series).join(MeetupEvent)
        .where(Series.user_id == user.id, MeetupEvent.meetup_id.in_([m.id for m in meetups]))
        .order_by(MeetupEvent.id)
        .options(selectinload(Series.attempts).selectinload(Attempt.history))
    ).all()

    personal = {
        (event_id, record_type): row.series_id
        for event_id, best in personal_bests(user.id).items()
        for record_type, row in best.items() if row is not None
    }
    club_records = {
        (record.type.value, record.series_id)
        for record in db.session.scalars(
            db.select(ClubRecord).where(ClubRecord.user_id == user.id)
        )
    }

    def marks(series, record_type):
        result = []
        if (record_type, series.id) in club_records:
            result.append("LR")
        if personal.get((series.meetup_event.event_id, record_type)) == series.id:
            result.append("PB")
        return result

    events = {meetup.id: [] for meetup in meetups}
    for series in series_list:
        meetup_event = series.meetup_event
        attempts = [None] * ATTEMPTS_COUNT[meetup_event.format.value]
        for attempt in series.attempts:
            attempts[attempt.attempt_number - 1] = serialize_attempt(attempt)
        events[meetup_event.meetup_id].append({
            "event_id": meetup_event.event_id,
            "format": meetup_event.format.value,
            "status": series.status.value,
            "attempts": attempts,
            "best": series.best,
            "average": series.average,
            "marks": {"single": marks(series, "single"), "average": marks(series, "average")},
        })

    return {
        "meetups": [
            {
                **serialize_meetup_ref(meetup),
                "status": meetup.status.value,
                "events": events[meetup.id],
            }
            for meetup in meetups
        ],
        "has_more": has_more,
    }
