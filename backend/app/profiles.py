"""Public pages: club records and member profile.

Routes: /api/clubs/<id>/records, /api/users/<id>, /api/users/<id>/meetups.
Open to everyone including guests, so only the id and name are returned for a person,
without the login. Rules: "Records" in docs/ARCHITECTURE.md. A deleted account
that kept its name has no profile (User.has_profile).

Results of meetups where the person was disqualified are not shown in the profile
and do not count towards PB. A club ban does not affect the profile: past
results and records stay, only the club disappears from the club list.
"""

from flask import Blueprint, request
from sqlalchemy.orm import selectinload

from .errors import ApiError
from .events import EVENTS
from .extensions import db
from .meetups import iso_utc
from .models import (
    Attempt, Club, ClubMember, ClubRecord, Disqualification, Meetup, MeetupEvent, RecordType,
    Series, User,
)
from .permissions import get_or_404
from .results import ATTEMPTS_COUNT
from .scoring import best_result, not_disqualified, serialize_attempt, solution_visible

profiles = Blueprint("profiles", __name__)

PAGE_SIZE = 10


def public_user(user):
    # has_profile: whether the name can link to a profile (User.has_profile).
    return {"id": user.id, "display_name": user.display_name, "has_profile": user.has_profile}


def get_profile_user(user_id):
    """User with a public profile, otherwise 404."""
    user = get_or_404(User, user_id, "Участник не найден")
    if not user.has_profile:
        raise ApiError(404, "not_found", "Участник не найден")
    return user


def serialize_meetup_ref(meetup):
    return {
        "id": meetup.id,
        "date": meetup.date.isoformat(),
        "club": {"id": meetup.club.id, "name": meetup.club.name},
    }


# Club records

@profiles.get("/clubs/<int:club_id>/records")
def club_records(club_id):
    """Club records from the club_records cache: single and average per event.

    Only events with at least one record, in EVENTS order.
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


# Member profile

def attended_meetups(user_id):
    """Conditions for a query on Meetup: the person has a series and is not disqualified."""
    has_series = db.select(Series.id).join(MeetupEvent).where(
        MeetupEvent.meetup_id == Meetup.id, Series.user_id == user_id,
    ).exists()
    disqualified = db.select(Disqualification.id).where(
        Disqualification.meetup_id == Meetup.id, Disqualification.user_id == user_id,
    ).exists()
    return has_series, ~disqualified


def personal_bests(user_id):
    """The person's best results across all clubs: {event_id: {"single": row, "average": row}}.

    Only events where they have series. A row comes from best_result, or None
    if there are no successful results.
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
    """Name, clubs, number of meetups and personal bests (PB) per event."""
    user = get_profile_user(user_id)
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
    """Meetup history with results, newest first, PAGE_SIZE meetups at a time.

    ?offset= is how many meetups are already loaded. PB and LR marks are current records only.
    """
    user = get_profile_user(user_id)
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
        show_solution = solution_visible(series)
        attempts = [None] * ATTEMPTS_COUNT[meetup_event.format.value]
        for attempt in series.attempts:
            attempts[attempt.attempt_number - 1] = serialize_attempt(attempt, show_solution)
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
