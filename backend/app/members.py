"""Club members: public list and member management. Routes /api/clubs/<id>/members…

The list is visible to everyone (without banned members). The member card and actions
are for club organizers and the administrator. Rules: "Roles",
"Disqualification and bans" and "Authentication" in docs/ARCHITECTURE.md.
"""

from flask import Blueprint, request
from flask_login import current_user
from sqlalchemy import func

from .accounts import create_account, reset_password
from .auth import throttle
from .desk import parse_reason
from .errors import ApiError
from .extensions import db
from .forms import json_body
from .meetups import iso_utc
from .models import (
    Club, ClubMember, ClubRecord, ClubRole, Meetup, MeetupEvent, MeetupParticipant, MeetupStatus,
    ParticipantStatus, Series, User, utcnow,
)
from .permissions import get_or_404, is_active_organizer, is_last_organizer, require_club_manager
from .scoring import event_table

members = Blueprint("members", __name__)

FILTERS = ("all", "organizers", "banned")


def get_member(club_id, user_id):
    membership = db.session.get(ClubMember, (club_id, user_id))
    if membership is None:
        raise ApiError(404, "not_found", "Участник не найден")
    return membership


def can_manage(club_id):
    """The administrator or an organizer who has accepted the pledge: they see logins and banned members."""
    return current_user.is_authenticated and (current_user.is_admin or is_active_organizer(club_id))


def meetups_counts(club_id):
    """Number of club meetups where the user has at least one series: {user_id: n}.

    Series exist only at started meetups, so these are exactly the attended meetups.
    """
    return dict(db.session.execute(
        db.select(Series.user_id, func.count(func.distinct(MeetupEvent.meetup_id)))
        .join(MeetupEvent)
        .join(Meetup)
        .where(Meetup.club_id == club_id)
        .group_by(Series.user_id)
    ).all())


def records_counts(club_id):
    """Number of current club records (LR) per user: {user_id: n}."""
    return dict(db.session.execute(
        db.select(ClubRecord.user_id, func.count())
        .where(ClubRecord.club_id == club_id)
        .group_by(ClubRecord.user_id)
    ).all())


def serialize_ban(membership):
    if membership.banned_at is None:
        return None
    banned_by = db.session.get(User, membership.banned_by) if membership.banned_by else None
    return {
        "reason": membership.ban_reason,
        "banned_at": iso_utc(membership.banned_at),
        "banned_by": None if banned_by is None else {
            "id": banned_by.id, "display_name": banned_by.display_name,
        },
    }


# List

@members.get("/clubs/<int:club_id>/members")
def list_members(club_id):
    """Club members with search by name (and by login for organizers).

    Organizers and the administrator also see banned members, logins, filters and
    the number of people in each filter. Nobody else gets logins. Search is in Python:
    LOWER in SQLite does not handle Cyrillic.
    """
    get_or_404(Club, club_id, "Клуб не найден")
    manager = can_manage(club_id)
    query = request.args.get("q", "").strip().casefold()
    selected = request.args.get("filter", "all")
    if selected not in FILTERS or not manager:
        selected = "all"

    memberships = db.session.scalars(
        db.select(ClubMember).where(ClubMember.club_id == club_id)
    ).all()
    if not manager:
        memberships = [m for m in memberships if m.banned_at is None]
    counts = meetups_counts(club_id)
    records = records_counts(club_id)

    def in_filter(membership, name):
        if name == "organizers":
            return membership.role == ClubRole.ORGANIZER
        if name == "banned":
            return membership.banned_at is not None
        return True

    found = [
        m for m in memberships
        if query in m.user.display_name.casefold() or (manager and query in m.user.login)
    ]

    def serialize(membership):
        user = {"id": membership.user.id, "display_name": membership.user.display_name}
        if manager:
            user["login"] = membership.user.login
        return {
            "user": user,
            "role": membership.role.value,
            "banned": membership.banned_at is not None,
            "meetups_count": counts.get(membership.user_id, 0),
            "records_count": records.get(membership.user_id, 0),
        }

    result = {
        "members": [
            serialize(m)
            for m in sorted(
                (m for m in found if in_filter(m, selected)),
                key=lambda m: m.user.display_name,
            )
        ],
        "can_manage": manager,
    }
    if manager:
        result["filter_counts"] = {
            name: sum(1 for m in found if in_filter(m, name)) for name in FILTERS
        }
    return result


@members.post("/clubs/<int:club_id>/members")
def create_member(club_id):
    """New account with a temporary password, added to the club right away (for a newcomer without a phone)."""
    club = get_or_404(Club, club_id, "Клуб не найден")
    require_club_manager(club.id)
    user, password = create_account(json_body())
    db.session.add(ClubMember(club_id=club.id, user_id=user.id))
    db.session.commit()
    return {
        "user": {"id": user.id, "display_name": user.display_name, "login": user.login},
        "temporary_password": password,
    }, 201


# Member card

def restrictions(membership):
    """Why an action is unavailable: {action: reason, or None if allowed}.

    The action endpoints run the same checks, and the frontend shows the reason
    next to the disabled button.
    """
    return {
        "reset_password": reset_password_restriction(membership),
        "organizer": organizer_restriction(membership),
        "ban": ban_restriction(membership),
    }


def reset_password_restriction(membership):
    user = membership.user
    if user.id == current_user.id:
        return "Свой пароль меняется в профиле"
    if current_user.is_admin:
        return None
    if user.is_admin:
        return "Пароль администратора сбрасывает администратор"
    if membership.role == ClubRole.ORGANIZER:
        return "Пароль организатора сбрасывает администратор"
    # An organizer of any club, not just this one: otherwise an organizer of one club
    # could log in as an organizer of another. The reason does not name the role:
    # the organizer of this club must not learn about the member's role in another club.
    if db.session.scalar(db.select(ClubMember.user_id).where(
        ClubMember.user_id == user.id, ClubMember.role == ClubRole.ORGANIZER,
    ).limit(1)):
        return "Пароль этого участника сбрасывает администратор"
    return None


def organizer_restriction(membership):
    if membership.role == ClubRole.ORGANIZER:
        if is_last_organizer(membership.club_id, membership.user_id):
            return "Нельзя снять последнего организатора"
        return None
    if membership.banned_at is not None:
        return "Сначала разблокируйте участника"
    return None


def ban_restriction(membership):
    if membership.banned_at is not None:
        return None  # unbanning is always allowed
    if membership.user_id == current_user.id:
        return "Нельзя заблокировать самого себя"
    if membership.role == ClubRole.ORGANIZER:
        return "Сначала снимите права организатора"
    return None


def require_allowed(reason):
    if reason is not None:
        raise ApiError(409, "not_allowed", reason)


def meetups_with_results(user_id, club_id=None):
    """Meetups with the user's series, newest first, with their results.

    Only the club's meetups if club_id is given (member card), otherwise all clubs
    (administrator's user card): then every meetup names its club.
    """
    query = (
        db.select(Series)
        .join(MeetupEvent)
        .join(Meetup)
        .where(Series.user_id == user_id)
        .order_by(Meetup.date.desc(), Meetup.starts_at.desc(), MeetupEvent.id)
    )
    if club_id is not None:
        query = query.where(Meetup.club_id == club_id)
    rows = db.session.scalars(query).all()

    meetups = {}
    for series in rows:
        meetup_event = series.meetup_event
        meetup = meetup_event.meetup
        if meetup.id not in meetups:
            disqualification = next(
                (d for d in meetup.disqualifications if d.user_id == series.user_id), None,
            )
            meetups[meetup.id] = {
                "id": meetup.id,
                "date": meetup.date.isoformat(),
                "place": meetup.place,
                "status": meetup.status.value,
                "disqualification": None if disqualification is None else {
                    "reason": disqualification.reason,
                    "created_at": iso_utc(disqualification.created_at),
                },
                "events": [],
            }
            if club_id is None:
                meetups[meetup.id]["club"] = {"id": meetup.club.id, "name": meetup.club.name}
        # Place and record marks come from the event table. A disqualified user has none.
        row = next((r for r in event_table(meetup_event) if r["series"].id == series.id), None)
        meetups[meetup.id]["events"].append({
            "event_id": meetup_event.event_id,
            "format": meetup_event.format.value,
            "status": series.status.value,
            "best": series.best,
            "average": series.average,
            "place": row["place"] if row else None,
            "marks": row["marks"] if row else {"single": [], "average": []},
        })
    return list(meetups.values())


def live_meetup(membership):
    """The club's live meetup where the member is approved: a ban interrupts their series."""
    meetup = db.session.scalar(
        db.select(Meetup).join(MeetupParticipant).where(
            Meetup.club_id == membership.club_id,
            Meetup.status == MeetupStatus.LIVE,
            MeetupParticipant.user_id == membership.user_id,
            MeetupParticipant.status == ParticipantStatus.APPROVED,
        ).limit(1)
    )
    return None if meetup is None else {"id": meetup.id, "date": meetup.date.isoformat()}


def member_card(membership):
    user = membership.user
    meetups = meetups_with_results(membership.user_id, membership.club_id)
    return {
        "user": {"id": user.id, "display_name": user.display_name, "login": user.login},
        "role": membership.role.value,
        "joined_at": iso_utc(membership.joined_at),
        "ban": serialize_ban(membership),
        "meetups_count": len(meetups),
        "meetups": meetups,
        "live_meetup": live_meetup(membership),
        "restrictions": restrictions(membership),
    }


def get_managed_member(club_id, user_id):
    get_or_404(Club, club_id, "Клуб не найден")
    require_club_manager(club_id)
    return get_member(club_id, user_id)


@members.get("/clubs/<int:club_id>/members/<int:user_id>")
def get_member_card(club_id, user_id):
    return {"member": member_card(get_managed_member(club_id, user_id))}


# Actions

@members.post("/clubs/<int:club_id>/members/<int:user_id>/password-reset")
def reset_member_password(club_id, user_id):
    """Temporary password, shown once. All of the member's sessions end."""
    membership = get_managed_member(club_id, user_id)
    require_allowed(reset_password_restriction(membership))
    password = reset_password(membership.user)
    # If the member was locked out by login throttling, the new password works right away.
    throttle.clear_failures(membership.user.login)
    db.session.commit()
    return {"temporary_password": password}


@members.put("/clubs/<int:club_id>/members/<int:user_id>/organizer")
def make_organizer(club_id, user_id):
    membership = get_managed_member(club_id, user_id)
    if membership.role != ClubRole.ORGANIZER:
        require_allowed(organizer_restriction(membership))
        membership.role = ClubRole.ORGANIZER
        db.session.commit()
    return {"member": member_card(membership)}


@members.delete("/clubs/<int:club_id>/members/<int:user_id>/organizer")
def remove_organizer(club_id, user_id):
    """Removes organizer rights; the user stays in the club. One can remove them from oneself."""
    membership = get_managed_member(club_id, user_id)
    if membership.role == ClubRole.ORGANIZER:
        require_allowed(organizer_restriction(membership))
        membership.role = ClubRole.MEMBER
        db.session.commit()
    return {"member": member_card(membership)}


@members.put("/clubs/<int:club_id>/members/<int:user_id>/ban")
def ban_member(club_id, user_id):
    """Ban: no joining requests and no attempt submissions, including at a live meetup.

    Already submitted attempts, tables and records do not change. A repeated request changes the reason.
    """
    membership = get_managed_member(club_id, user_id)
    require_allowed(ban_restriction(membership))
    reason = parse_reason()
    if membership.banned_at is None:
        membership.banned_at = utcnow()
        membership.banned_by = current_user.id
    membership.ban_reason = reason
    db.session.commit()
    return {"member": member_card(membership)}


@members.delete("/clubs/<int:club_id>/members/<int:user_id>/ban")
def unban_member(club_id, user_id):
    membership = get_managed_member(club_id, user_id)
    membership.banned_at = None
    membership.banned_by = None
    membership.ban_reason = None
    db.session.commit()
    return {"member": member_card(membership)}
