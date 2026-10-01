"""Meetups and taking part in them.

Routes: /api/clubs/<id>/meetups, /api/meetups/…, /api/join/<token>.
Rules: "Meetups" in docs/ARCHITECTURE.md.
"""

import re
import secrets
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .errors import ApiError
from .events import EVENT_ORDER, EVENTS
from .extensions import db
from .forms import collapse_spaces, get_list, get_str, json_body, raise_if_errors
from .models import (
    Attempt, Club, ClubMember, FmcAttempt, Format, Meetup, MeetupEvent, MeetupParticipant,
    MeetupStatus, ParticipantStatus, Scramble, Series, utcnow,
)
from .permissions import (
    get_membership, get_or_404, is_active_organizer, is_banned, is_organizer, my_role,
    pending_pledge, require_organizer,
)
from .results import ATTEMPTS_COUNT, DNF
from .scoring import AVERAGE_FORMATS, event_table

meetups = Blueprint("meetups", __name__)

MAX_SCRAMBLE_LENGTH = 1000
# Statuses in which the meetup accepts requests and participants.
OPEN_STATUSES = (MeetupStatus.PLANNED, MeetupStatus.LIVE)
TIME_RE = re.compile(r"\d{2}:\d{2}")


def iso_utc(moment):
    """UTC timestamp from the DB (without time zone) to ISO with "Z"."""
    return moment.isoformat() + "Z" if moment else None


def new_join_token():
    return secrets.token_urlsafe(24)


def join_url(token):
    """Meetup link for sharing and the QR code, built from SITE_URL."""
    return f"{current_app.config['SITE_URL']}/join/{token}"


def approved_counts(meetup_ids):
    """Number of approved participants per meetup: {meetup_id: n}."""
    rows = db.session.execute(
        db.select(MeetupParticipant.meetup_id, db.func.count())
        .where(
            MeetupParticipant.meetup_id.in_(meetup_ids),
            MeetupParticipant.status == ParticipantStatus.APPROVED,
        )
        .group_by(MeetupParticipant.meetup_id)
    ).all()
    return dict(rows)


def serialize_summary(meetup, participants_count):
    return {
        "id": meetup.id,
        "date": meetup.date.isoformat(),
        "starts_at": iso_utc(meetup.starts_at),
        "ends_at": iso_utc(meetup.ends_at),
        "place": meetup.place,
        "address": meetup.address,
        "status": meetup.status.value,
        "events": [event.event_id for event in meetup.events],
        "participants_count": participants_count,
    }


def serialize_meetup(meetup):
    # Number of participants in an event is the number of started series.
    series_counts = dict(db.session.execute(
        db.select(Series.meetup_event_id, db.func.count())
        .join(MeetupEvent)
        .where(MeetupEvent.meetup_id == meetup.id)
        .group_by(Series.meetup_event_id)
    ).all())
    result = serialize_summary(meetup, approved_counts([meetup.id]).get(meetup.id, 0))
    result["club"] = {
        "id": meetup.club.id, "name": meetup.club.name, "timezone": meetup.club.timezone,
    }
    result["events"] = [
        {
            "id": event.id,
            "event_id": event.event_id,
            "format": event.format.value,
            "participants_count": series_counts.get(event.id, 0),
        }
        for event in meetup.events
    ]
    if is_active_organizer(meetup.club_id):
        # The join link is for organizers only and only while it is valid.
        if meetup.status in OPEN_STATUSES:
            result["join_token"] = meetup.join_token
            result["join_url"] = join_url(meetup.join_token)
        result["cancel_restriction"] = cancel_restriction(meetup)
    return result


def serialize_request(participant):
    return {
        "user": {
            "id": participant.user.id,
            "display_name": participant.user.display_name,
            "login": participant.user.login,
        },
        "status": participant.status.value,
        "requested_at": iso_utc(participant.requested_at),
        "decided_at": iso_utc(participant.decided_at),
    }


def get_meetup(meetup_id):
    return get_or_404(Meetup, meetup_id, "Встреча не найдена")


def require_open(meetup):
    """Planned or live: a finished or cancelled meetup takes no requests or participants."""
    if meetup.status == MeetupStatus.FINISHED:
        raise ApiError(409, "meetup_finished", "Встреча уже завершена")
    if meetup.status == MeetupStatus.CANCELLED:
        raise ApiError(409, "meetup_cancelled", "Встреча отменена")


def cancel_restriction(meetup):
    """Why the meetup cannot be cancelled, or None.

    Only before the first result: any saved attempt or a started FMC hour blocks it.
    """
    if meetup.status == MeetupStatus.FINISHED:
        return "Встреча уже завершена"
    if meetup.status == MeetupStatus.CANCELLED:
        return "Встреча уже отменена"
    in_meetup = Series.meetup_event_id.in_(
        db.select(MeetupEvent.id).where(MeetupEvent.meetup_id == meetup.id)
    )
    if db.session.scalar(db.select(db.exists().where(Attempt.series_id == Series.id, in_meetup))):
        return "Участники уже сдали попытки"
    if db.session.scalar(db.select(db.exists().where(FmcAttempt.series_id == Series.id, in_meetup))):
        return "Участники уже начали попытки FMC"
    return None


# Club meetups

@meetups.get("/clubs/<int:club_id>/meetups")
def list_club_meetups(club_id):
    get_or_404(Club, club_id, "Клуб не найден")
    items = db.session.scalars(
        db.select(Meetup)
        .where(Meetup.club_id == club_id)
        .options(selectinload(Meetup.events))
        .order_by(Meetup.date.desc(), Meetup.starts_at.desc())
    ).all()
    counts = approved_counts([meetup.id for meetup in items])
    return {"meetups": [serialize_summary(m, counts.get(m.id, 0)) for m in items]}


@meetups.post("/clubs/<int:club_id>/meetups")
def create_meetup(club_id):
    club = get_or_404(Club, club_id, "Клуб не найден")
    require_organizer(club.id)

    data = json_body()
    club_zone = ZoneInfo(club.timezone)
    meetup_date, date_error = parse_date(get_str(data, "date"), club_zone)
    starts_at, starts_error = parse_time(get_str(data, "starts_at"), required=True)
    ends_at, ends_error = parse_time(get_str(data, "ends_at"), required=False)
    if starts_at and ends_at and ends_at <= starts_at:
        ends_error = "Окончание должно быть позже начала"
    place = collapse_spaces(get_str(data, "place"))
    address = collapse_spaces(get_str(data, "address"))
    events, event_errors = parse_events(get_list(data, "events"))

    errors = {
        "date": date_error,
        "starts_at": starts_error,
        "ends_at": ends_error,
        "place": "Укажите место" if not place else (
            "Максимум 200 символов" if len(place) > 200 else None
        ),
        "address": "Максимум 300 символов" if len(address) > 300 else None,
    }
    errors.update(event_errors)
    raise_if_errors(errors)

    meetup = Meetup(
        club_id=club.id,
        date=meetup_date,
        starts_at=to_utc(meetup_date, starts_at, club_zone),
        ends_at=to_utc(meetup_date, ends_at, club_zone) if ends_at else None,
        place=place,
        address=address or None,
        status=MeetupStatus.PLANNED,
        join_token=new_join_token(),
        created_by=current_user.id,
    )
    # Until the meetup is reloaded, the events stay in the order of appending.
    for event_id, series_format, scrambles in sorted(events, key=lambda e: EVENT_ORDER[e[0]]):
        meetup.events.append(MeetupEvent(
            event_id=event_id,
            format=series_format,
            scrambles=[
                Scramble(attempt_number=number, scramble=scramble)
                for number, scramble in enumerate(scrambles, 1)
            ],
        ))
    db.session.add(meetup)
    db.session.commit()
    return {"meetup": serialize_meetup(meetup)}, 201


def parse_date(value, club_zone):
    """Meetup date and error. A past date (by the club's clock) is not accepted."""
    try:
        result = date.fromisoformat(value)
    except ValueError:
        return None, "Укажите дату"
    if result < datetime.now(club_zone).date():
        return None, "Дата уже прошла"
    return result, None


def parse_time(value, required):
    """Time "HH:MM" and error. An empty optional time gives (None, None)."""
    if not value:
        return None, "Укажите время" if required else None
    try:
        if not TIME_RE.fullmatch(value):
            raise ValueError
        return time.fromisoformat(value), None
    except ValueError:
        return None, "Неверное время"


def to_utc(local_date, local_time, club_zone):
    """Date and time by the club's clock → UTC without time zone, as stored in the DB."""
    moment = datetime.combine(local_date, local_time, tzinfo=club_zone)
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def parse_events(items):
    """List of (event_id, format, scrambles) and field errors like events.2.scrambles.

    Scrambles are generated by the organizer's browser; the server checks only
    their count for the format, that they are non-empty, and their length.
    """
    events, errors, seen = [], {}, set()
    if not items:
        return events, {"events": "Выберите хотя бы одну дисциплину"}
    for index, item in enumerate(items):
        item = item if isinstance(item, dict) else {}
        event_id = get_str(item, "event_id")
        series_format = get_str(item, "format")
        scrambles = get_list(item, "scrambles")
        field = f"events.{index}"

        if event_id not in EVENTS:
            errors[f"{field}.event_id"] = "Неизвестная дисциплина"
            continue
        if event_id in seen:
            errors[f"{field}.event_id"] = "Дисциплина выбрана дважды"
            continue
        seen.add(event_id)
        if series_format not in Format:
            errors[f"{field}.format"] = "Неизвестный формат"
            continue

        scrambles = [
            collapse_spaces(s) if isinstance(s, str) else "" for s in scrambles
        ]
        if len(scrambles) != ATTEMPTS_COUNT[series_format]:
            errors[f"{field}.scrambles"] = "Число скрамблов не совпадает с форматом"
        elif not all(0 < len(s) <= MAX_SCRAMBLE_LENGTH for s in scrambles):
            errors[f"{field}.scrambles"] = "Пустой или слишком длинный скрамбл"
        else:
            events.append((event_id, Format(series_format), scrambles))
    return events, errors


# Meetup

@meetups.get("/meetups/<int:meetup_id>")
def get_meetup_page(meetup_id):
    meetup = get_meetup(meetup_id)
    my_request = None
    if current_user.is_authenticated:
        participant = db.session.get(MeetupParticipant, (meetup.id, current_user.id))
        if participant:
            my_request = {"status": participant.status.value}
    result = serialize_meetup(meetup)
    for event, meetup_event in zip(result["events"], meetup.events):
        event.update(event_standing(meetup_event))
    return {
        "meetup": result,
        "my_role": my_role(meetup.club_id),
        "my_request": my_request,
        "pledge": pending_pledge(meetup.club_id),
    }


def event_standing(meetup_event):
    """For the event card: the table leader and the current user's series."""
    rows = event_table(meetup_event)
    leader = None
    if rows and rows[0]["place"] == 1:
        series = rows[0]["series"]
        # In formats with an average the leader is shown by the average, if there is one.
        use_average = meetup_event.format in AVERAGE_FORMATS and series.average != DNF
        leader = {
            "display_name": series.user.display_name,
            "value": series.average if use_average else series.best,
            "is_average": use_average,
        }

    my_series = None
    if current_user.is_authenticated:
        mine = next(
            (row for row in rows if row["series"].user_id == current_user.id), None,
        )
        if mine:
            series = mine["series"]
            my_series = {
                "status": series.status.value,
                "attempts_done": len(series.attempts),
                "best": series.best,
                "average": series.average,
                "place": mine["place"],
                "total": len(rows),
            }
    return {"leader": leader, "my_series": my_series}


@meetups.post("/meetups/<int:meetup_id>/start")
def start_meetup(meetup_id):
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    if meetup.status != MeetupStatus.PLANNED:
        raise ApiError(409, "invalid_status", "Встреча уже запущена или завершена")
    meetup.status = MeetupStatus.LIVE
    db.session.commit()
    return {"meetup": serialize_meetup(meetup)}


@meetups.post("/meetups/<int:meetup_id>/cancel")
def cancel_meetup(meetup_id):
    """Cancels a meetup without results. It stays in the club list with the "cancelled" status.

    Requests, scrambles and empty series are deleted, the join link stops working.
    The events stay: the meetup card shows what was planned.
    """
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    if reason := cancel_restriction(meetup):
        raise ApiError(409, "cannot_cancel", reason)
    for meetup_event in meetup.events:
        meetup_event.scrambles.clear()
        meetup_event.series.clear()
    meetup.participants.clear()
    meetup.status = MeetupStatus.CANCELLED
    meetup.join_token = None
    db.session.commit()
    return {"meetup": serialize_meetup(meetup)}


@meetups.post("/meetups/<int:meetup_id>/token")
def reissue_token(meetup_id):
    """New meetup link. The old one stops working, requests stay."""
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    require_open(meetup)
    meetup.join_token = new_join_token()
    db.session.commit()
    return {"join_token": meetup.join_token, "join_url": join_url(meetup.join_token)}


# Joining by link

def get_meetup_by_token(token):
    meetup = db.session.scalar(db.select(Meetup).where(Meetup.join_token == token))
    # After the meetup is finished or cancelled the link is invalid.
    if meetup is None or meetup.status not in OPEN_STATUSES:
        raise ApiError(404, "invalid_link", "Ссылка на встречу недействительна")
    return meetup


@meetups.get("/join/<token>")
def join_preview(token):
    """Data for the meetup banner on the login page, available by link without logging in."""
    meetup = get_meetup_by_token(token)
    return {"meetup": {
        "id": meetup.id,
        "date": meetup.date.isoformat(),
        "starts_at": iso_utc(meetup.starts_at),
        "place": meetup.place,
        "club": {
            "id": meetup.club.id, "name": meetup.club.name, "timezone": meetup.club.timezone,
        },
    }}


@meetups.post("/join/<token>")
@login_required
def join_meetup(token):
    meetup = get_meetup_by_token(token)
    user = current_user._get_current_object()

    participant = db.session.get(MeetupParticipant, (meetup.id, user.id))
    if participant:
        return {"meetup_id": meetup.id, "status": participant.status.value}
    if is_banned(meetup.club_id, user):
        raise ApiError(403, "banned", "Вы заблокированы в этом клубе")

    participant = MeetupParticipant(meetup_id=meetup.id, user_id=user.id)
    db.session.add(participant)
    # The organizer takes part without approval.
    if is_organizer(meetup.club_id):
        approve(meetup, participant)
    try:
        db.session.commit()
    except IntegrityError:
        # A concurrent request has already created the request (double tap).
        db.session.rollback()
        participant = db.session.get(MeetupParticipant, (meetup.id, user.id))
        return {"meetup_id": meetup.id, "status": participant.status.value}
    return {"meetup_id": meetup.id, "status": participant.status.value}, 201


# Requests (organizer)

def approve(meetup, participant):
    """Approves a request. On the first approval the user joins the club."""
    participant.status = ParticipantStatus.APPROVED
    participant.decided_at = utcnow()
    participant.decided_by = current_user.id
    if get_membership(meetup.club_id, participant.user) is None:
        db.session.add(ClubMember(club_id=meetup.club_id, user_id=participant.user_id))


def get_participant(meetup, user_id):
    participant = db.session.get(MeetupParticipant, (meetup.id, user_id))
    if participant is None:
        raise ApiError(404, "not_found", "Заявка не найдена")
    return participant


@meetups.get("/meetups/<int:meetup_id>/requests")
def list_requests(meetup_id):
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    participants = db.session.scalars(
        db.select(MeetupParticipant)
        .where(MeetupParticipant.meetup_id == meetup.id)
        .options(selectinload(MeetupParticipant.user))
        .order_by(MeetupParticipant.requested_at)
    ).all()
    # Pending first, within groups by request time.
    participants.sort(key=lambda p: p.status != ParticipantStatus.PENDING)
    return {"requests": [serialize_request(p) for p in participants]}


@meetups.post("/meetups/<int:meetup_id>/requests/<int:user_id>/approve")
def approve_request(meetup_id, user_id):
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    require_open(meetup)
    participant = get_participant(meetup, user_id)
    if participant.status != ParticipantStatus.APPROVED:
        if is_banned(meetup.club_id, participant.user):
            raise ApiError(409, "banned", "Участник заблокирован в клубе")
        approve(meetup, participant)
        db.session.commit()
    return {"request": serialize_request(participant)}


@meetups.post("/meetups/<int:meetup_id>/requests/<int:user_id>/reject")
def reject_request(meetup_id, user_id):
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    require_open(meetup)
    participant = get_participant(meetup, user_id)
    if participant.status != ParticipantStatus.PENDING:
        raise ApiError(409, "invalid_status", "Отклонить можно только ожидающую заявку")
    participant.status = ParticipantStatus.REJECTED
    participant.decided_at = utcnow()
    participant.decided_by = current_user.id
    db.session.commit()
    return {"request": serialize_request(participant)}


@meetups.post("/meetups/<int:meetup_id>/requests/approve-all")
def approve_all_requests(meetup_id):
    """Approves all pending requests except those from users banned in the club."""
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    require_open(meetup)
    pending = db.session.scalars(
        db.select(MeetupParticipant).where(
            MeetupParticipant.meetup_id == meetup.id,
            MeetupParticipant.status == ParticipantStatus.PENDING,
        )
    ).all()
    approved = 0
    for participant in pending:
        if not is_banned(meetup.club_id, participant.user):
            approve(meetup, participant)
            approved += 1
    db.session.commit()
    return {"approved": approved}
