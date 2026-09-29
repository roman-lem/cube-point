"""Administration: clubs and their organizers, users, meetup deletion, names of deleted accounts.

Routes /api/admin/…

Administrators only (users.is_admin). Rules: "Roles" in docs/ARCHITECTURE.md.
The first administrator is created with `flask make-admin LOGIN`.
"""

from zoneinfo import available_timezones

import click
from flask import Blueprint, request
from flask.cli import with_appcontext
from flask_login import current_user
from sqlalchemy import delete, func
from werkzeug.security import generate_password_hash

# auth before accounts: accounts and auth.routes import each other.
from .auth import throttle
from .auth.validation import login_error, name_error, normalize_login, password_error
from .accounts import reset_password  # noqa: I001
from .clubs import text_error
from .errors import ApiError, ValidationError
from .extensions import db
from .forms import collapse_spaces, get_str, json_body, raise_if_errors
from .meetups import iso_utc
from .members import meetups_with_results
from .models import (
    DELETED_USER_NAME, Attempt, Club, ClubMember, ClubRole, ConsentType, Meetup, MeetupEvent,
    MeetupParticipant, MeetupStatus, Series, User, UserConsent,
)
from .permissions import get_or_404, is_last_organizer
from .scoring import recalc_records

admin = Blueprint("admin", __name__, url_prefix="/admin")

DEFAULT_TIMEZONE = "Asia/Yekaterinburg"  # Tyumen time
USER_SEARCH_LIMIT = 10
USERS_PAGE_SIZE = 30
USER_FILTERS = ("all", "admins", "organizers", "deleted")


@admin.before_request
def require_admin():
    # Check for the whole blueprint: a new endpoint cannot be left unprotected.
    if not current_user.is_authenticated:
        raise ApiError(401, "unauthorized", "Нужно войти")
    if not current_user.is_admin:
        raise ApiError(403, "forbidden", "Это может только администратор")


def serialize_user(user):
    return {"id": user.id, "display_name": user.display_name, "login": user.login}


def count_by_club(*conditions):
    """{club_id: number of club members} with extra conditions."""
    return dict(db.session.execute(
        db.select(ClubMember.club_id, func.count())
        .where(ClubMember.banned_at.is_(None), *conditions)
        .group_by(ClubMember.club_id)
    ).all())


# Meetups that are over or in progress: a planned one is never the "latest".
HELD = Meetup.status.in_([MeetupStatus.LIVE, MeetupStatus.FINISHED])


@admin.get("/clubs")
def list_clubs():
    members = count_by_club()
    organizers = count_by_club(ClubMember.role == ClubRole.ORGANIZER)
    last_meetups = dict(db.session.execute(
        db.select(Meetup.club_id, func.max(Meetup.date)).where(HELD).group_by(Meetup.club_id)
    ).all())
    return {"clubs": [
        {
            "id": club.id,
            "name": club.name,
            "city": club.city,
            "logo_color": club.logo_color,
            "members_count": members.get(club.id, 0),
            "organizers_count": organizers.get(club.id, 0),
            "last_meetup_date": (
                last_meetups[club.id].isoformat() if club.id in last_meetups else None
            ),
        }
        for club in db.session.scalars(db.select(Club).order_by(Club.name))
    ]}


def get_club(club_id):
    club = db.session.get(Club, club_id)
    if club is None:
        raise ApiError(404, "not_found", "Клуб не найден")
    return club


def club_details(club):
    organizers = sorted(
        (m.user for m in club.members if m.role == ClubRole.ORGANIZER),
        key=lambda user: user.display_name,
    )
    return {
        "id": club.id,
        "name": club.name,
        "city": club.city,
        "timezone": club.timezone,
        "logo_color": club.logo_color,
        "members_count": sum(1 for m in club.members if m.banned_at is None),
        "meetups_count": db.session.scalar(
            db.select(func.count()).select_from(Meetup).where(Meetup.club_id == club.id, HELD)
        ),
        "organizers": [serialize_user(user) for user in organizers],
        # What deleting the club takes with it, and why it cannot be deleted now (or None).
        "deletion": deletion_summary(club),
        "delete_restriction": delete_restriction(club),
    }


def deletion_summary(club):
    """All meetups (planned too), all members (banned too) and all saved attempts."""
    def count(query):
        return db.session.scalar(db.select(func.count()).select_from(query.subquery()))

    return {
        "meetups": count(db.select(Meetup.id).where(Meetup.club_id == club.id)),
        "members": len(club.members),
        "results": count(
            db.select(Attempt.id).join(Series).join(MeetupEvent).join(Meetup)
            .where(Meetup.club_id == club.id)
        ),
    }


def delete_restriction(club):
    has_live = db.session.scalar(
        db.select(Meetup.id)
        .where(Meetup.club_id == club.id, Meetup.status == MeetupStatus.LIVE)
        .limit(1)
    )
    if has_live is not None:
        return "Идёт встреча — удалить клуб можно после её завершения"
    return None


@admin.get("/clubs/<int:club_id>")
def get_club_details(club_id):
    return {"club": club_details(get_club(club_id))}


def find_user(login):
    login = normalize_login(login)
    if not login:
        return None
    return db.session.scalar(db.select(User).where(User.login == login))


@admin.post("/clubs")
def create_club():
    data = json_body()
    name = collapse_spaces(get_str(data, "name"))
    city = collapse_spaces(get_str(data, "city"))
    timezone = get_str(data, "timezone").strip() or DEFAULT_TIMEZONE
    organizer_login = get_str(data, "organizer_login")
    organizer = find_user(organizer_login)

    raise_if_errors({
        "name": text_error(name, 100, "Введите название"),
        "city": text_error(city, 100, "Введите город"),
        "timezone": None if timezone in available_timezones() else "Выберите часовой пояс из списка",
        "organizer_login": (
            "Выберите первого организатора" if not organizer_login.strip()
            else "Пользователь не найден" if organizer is None
            else None
        ),
    })

    club = Club(name=name, city=city, timezone=timezone)
    club.members.append(ClubMember(user_id=organizer.id, user=organizer, role=ClubRole.ORGANIZER))
    db.session.add(club)
    db.session.commit()
    return {"club": club_details(club)}, 201


@admin.delete("/clubs/<int:club_id>")
def delete_club(club_id):
    """Deletes the club with everything in it; users stay, only their membership goes.

    meetups.club_id is RESTRICT so a club is never deleted by accident: meetups are
    deleted here explicitly. Everything below them (events, scrambles, requests, series,
    attempts, their history, FMC attempts, disqualifications) and the club's links,
    members and records go by ON DELETE CASCADE. One transaction.
    Personal bests are computed from results, so nothing else needs recalculating.
    """
    club = get_club(club_id)
    if reason := delete_restriction(club):
        raise ApiError(409, "meetup_live", reason)
    # Names are saved with collapse_spaces, so only the edges are trimmed.
    if get_str(json_body(), "name").strip() != club.name:
        raise ValidationError({"name": "Название не совпадает"})

    db.session.execute(delete(Meetup).where(Meetup.club_id == club.id))
    db.session.delete(club)
    db.session.commit()
    return "", 204


@admin.post("/clubs/<int:club_id>/organizers")
def add_organizer(club_id):
    """Makes the user an organizer: a new club membership or a promotion of a member."""
    club = get_club(club_id)
    login = get_str(json_body(), "login")
    user = find_user(login)
    if user is None:
        raise ValidationError({
            "login": "Пользователь не найден" if login.strip() else "Введите логин",
        })

    membership = db.session.get(ClubMember, (club.id, user.id))
    if membership is None:
        club.members.append(ClubMember(user_id=user.id, user=user, role=ClubRole.ORGANIZER))
    elif membership.banned_at is not None:
        raise ApiError(409, "banned", "Пользователь заблокирован в клубе")
    else:
        membership.role = ClubRole.ORGANIZER
    db.session.commit()
    return {"club": club_details(club)}


@admin.delete("/clubs/<int:club_id>/organizers/<int:user_id>")
def remove_organizer(club_id, user_id):
    """Demotes an organizer to a member; they are not removed from the club."""
    club = get_club(club_id)
    membership = db.session.get(ClubMember, (club.id, user_id))
    if membership is None or membership.role != ClubRole.ORGANIZER:
        raise ApiError(404, "not_found", "Организатор не найден")
    if is_last_organizer(club.id, user_id):
        raise ApiError(409, "last_organizer", "Нельзя снять последнего организатора клуба")

    membership.role = ClubRole.MEMBER
    db.session.commit()
    return {"club": club_details(club)}


@admin.get("/users/lookup")
def lookup_users():
    """User search by part of the login, to pick an organizer."""
    query = normalize_login(request.args.get("q", ""))
    if not query:
        return {"users": []}
    users = db.session.scalars(
        db.select(User)
        .where(User.login.contains(query, autoescape=True))
        .order_by(User.login)
        .limit(USER_SEARCH_LIMIT)
    )
    return {"users": [serialize_user(user) for user in users]}


# All users

def kept_name_condition():
    """A deleted account that kept its name in results (DELETED_NAME consent)."""
    return User.deleted_at.is_not(None) & (
        db.select(UserConsent.id)
        .where(UserConsent.user_id == User.id, UserConsent.type == ConsentType.DELETED_NAME)
        .exists()
    )


def filter_condition(name):
    """Condition of a list filter.

    "all" leaves out fully anonymized deleted accounts: they have no login,
    email or name, they would only add identical DELETED_USER_NAME rows.
    """
    if name == "admins":
        return User.is_admin.is_(True)
    if name == "organizers":
        return (
            db.select(ClubMember.user_id)
            .where(ClubMember.user_id == User.id, ClubMember.role == ClubRole.ORGANIZER)
            .exists()
        )
    if name == "deleted":
        return kept_name_condition()
    return User.deleted_at.is_(None) | kept_name_condition()


def user_clubs(user_ids):
    """{user_id: [club with the role and the ban mark]}, clubs by name."""
    clubs = {user_id: [] for user_id in user_ids}
    rows = db.session.execute(
        db.select(ClubMember, Club).join(Club)
        .where(ClubMember.user_id.in_(user_ids))
        .order_by(Club.name, Club.id)
    ).all()
    for membership, club in rows:
        clubs[membership.user_id].append({
            "id": club.id,
            "name": club.name,
            "role": membership.role.value,
            "banned": membership.banned_at is not None,
        })
    return clubs


def user_rows(users):
    """List rows: account data and clubs with roles. Only the administrator gets the email."""
    ids = [user.id for user in users]
    clubs = user_clubs(ids)
    kept = set(db.session.scalars(
        db.select(User.id).where(User.id.in_(ids), kept_name_condition())
    ))
    return [
        {
            "id": user.id,
            "display_name": user.display_name,
            "login": user.login,
            "email": user.email,
            "created_at": iso_utc(user.created_at),
            "deleted_at": iso_utc(user.deleted_at) if user.deleted_at else None,
            "is_admin": user.is_admin,
            "kept_name": user.id in kept,
            "clubs": clubs[user.id],
        }
        for user in users
    ]


@admin.get("/users")
def list_users():
    """All users by name, USERS_PAGE_SIZE at a time.

    ?q= is part of the name, login or email, ?filter= one of USER_FILTERS,
    ?offset= how many are already loaded. The search is in Python, as in
    search_deleted_users: SQLite compares case-insensitively only for Latin letters;
    for a few hundred users this is enough.
    """
    query = collapse_spaces(request.args.get("q", "")).casefold()
    name = request.args.get("filter", "all")
    if name not in USER_FILTERS:
        name = "all"
    offset = max(request.args.get("offset", 0, type=int), 0)

    rows = db.session.execute(
        db.select(User.id, User.display_name, User.login, User.email)
        .where(filter_condition(name))
    ).all()
    found = sorted(
        (
            row for row in rows
            if any(query in (text or "").casefold() for text in row[1:])
        ),
        key=lambda row: (row.display_name.casefold(), row.id),
    )
    page_ids = [row.id for row in found[offset:offset + USERS_PAGE_SIZE]]
    users = {user.id: user for user in db.session.scalars(
        db.select(User).where(User.id.in_(page_ids))
    )}
    return {
        "users": user_rows([users[user_id] for user_id in page_ids]),
        "has_more": len(found) > offset + USERS_PAGE_SIZE,
    }


def latest_consents(user):
    """The latest entry of every consent type: {type: {version, accepted_at}}."""
    consents = {}
    for consent in db.session.scalars(
        db.select(UserConsent).where(UserConsent.user_id == user.id)
        .order_by(UserConsent.accepted_at, UserConsent.id)
    ):
        consents[consent.type.value] = {
            "version": consent.version,
            "accepted_at": iso_utc(consent.accepted_at),
        }
    return consents


def reset_password_restriction(user):
    """Why the administrator cannot reset the password, or None."""
    if user.id == current_user.id:
        return "Свой пароль меняется в профиле"
    if user.deleted_at is not None:
        return "Аккаунт удалён"
    return None


@admin.get("/users/<int:user_id>")
def get_user(user_id):
    user = get_or_404(User, user_id, "Пользователь не найден")
    return {"user": {
        **user_rows([user])[0],
        "consents": latest_consents(user),
        "meetups": meetups_with_results(user.id),
        "restrictions": {"reset_password": reset_password_restriction(user)},
    }}


@admin.post("/users/<int:user_id>/password-reset")
def reset_user_password(user_id):
    """Temporary password for anyone, organizers and administrators too; shown once.

    All of the user's sessions end (accounts.reset_password).
    """
    user = get_or_404(User, user_id, "Пользователь не найден")
    if reason := reset_password_restriction(user):
        raise ApiError(403, "forbidden", reason)
    password = reset_password(user)
    # If the user was locked out by login throttling, the new password works right away.
    throttle.clear_failures(user.login)
    db.session.commit()
    return {"temporary_password": password}


# Meetup deletion

def meetup_deletion(meetup):
    """What deleting the meetup takes with it and why it cannot be deleted now (or None)."""
    def count(query):
        return db.session.scalar(db.select(func.count()).select_from(query.subquery()))

    series = db.select(Series.id).join(MeetupEvent).where(MeetupEvent.meetup_id == meetup.id)
    return {
        "deletion": {
            "requests": count(
                db.select(MeetupParticipant.user_id)
                .where(MeetupParticipant.meetup_id == meetup.id)
            ),
            "participants": count(
                db.select(Series.user_id).join(MeetupEvent)
                .where(MeetupEvent.meetup_id == meetup.id).distinct()
            ),
            "results": count(db.select(Attempt.id).where(Attempt.series_id.in_(series))),
        },
        "delete_restriction": (
            "Идёт встреча — удалить её можно после завершения"
            if meetup.status == MeetupStatus.LIVE else None
        ),
    }


@admin.get("/meetups/<int:meetup_id>/deletion")
def get_meetup_deletion(meetup_id):
    return meetup_deletion(get_or_404(Meetup, meetup_id, "Встреча не найдена"))


@admin.delete("/meetups/<int:meetup_id>")
def delete_meetup(meetup_id):
    """Deletes a planned or finished meetup with everything in it, in one transaction.

    Events, scrambles, requests, series, attempts, their history, FMC attempts and
    disqualifications go by ON DELETE CASCADE, and so do the club records held by
    its series: the records of its events are then recalculated from the other meetups.
    Personal bests are computed from results, so nothing else needs recalculating.
    """
    meetup = get_or_404(Meetup, meetup_id, "Встреча не найдена")
    if reason := meetup_deletion(meetup)["delete_restriction"]:
        raise ApiError(409, "meetup_live", reason)

    club_id = meetup.club_id
    event_ids = [meetup_event.event_id for meetup_event in meetup.events]
    db.session.execute(delete(Meetup).where(Meetup.id == meetup.id))
    # Loaded objects may be gone from the DB now: the recalculation reads it anew.
    db.session.expire_all()
    for event_id in event_ids:
        recalc_records(club_id, event_id)
    db.session.commit()
    return "", 204


# Deleted accounts that kept their name (accounts.delete_account)

def kept_names():
    """Query of (user, DELETED_NAME consent) for deleted accounts that kept their name."""
    return (
        db.select(User, UserConsent)
        .join(UserConsent, UserConsent.user_id == User.id)
        .where(User.deleted_at.is_not(None), UserConsent.type == ConsentType.DELETED_NAME)
    )


@admin.get("/deleted-users")
def search_deleted_users():
    """Deleted accounts that kept their name, ?q= is part of the name.

    Filtered in Python: SQLite compares case-insensitively only for Latin letters,
    and there are only a few such accounts.
    """
    query = collapse_spaces(request.args.get("q", "")).casefold()
    rows = db.session.execute(kept_names().order_by(User.display_name, User.id)).all()
    return {"users": [
        {
            "id": user.id,
            "display_name": user.display_name,
            "deleted_at": iso_utc(user.deleted_at),
            "consent_version": consent.version,
        }
        for user, consent in rows if query in user.display_name.casefold()
    ]}


@admin.post("/deleted-users/<int:user_id>/anonymize")
def anonymize_user(user_id):
    """Withdraws the name consent: the name is replaced with the deleted-user name."""
    row = db.session.execute(kept_names().where(User.id == user_id)).first()
    if row is None:
        raise ApiError(404, "not_found", "Удалённый участник с сохранённым именем не найден")
    db.session.delete(row.UserConsent)
    row.User.display_name = DELETED_USER_NAME
    db.session.commit()
    return "", 204


@click.command("make-admin")
@click.argument("login")
@with_appcontext
def make_admin_command(login):
    """Grant administrator rights to user LOGIN (or create the user)."""
    user = find_user(login)
    if user is None:
        login = normalize_login(login)
        if error := login_error(login):
            raise click.ClickException(f"Login: {error}")
        click.echo(f"User {login} does not exist, creating a new one.")
        display_name = collapse_spaces(click.prompt("Name or nickname"))
        if error := name_error(display_name):
            raise click.ClickException(f"Name: {error}")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if error := password_error(password):
            raise click.ClickException(f"Password: {error}")
        user = User(
            login=login, display_name=display_name,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
    elif user.is_admin:
        click.echo(f"{user.login} is already an administrator.")
        return

    user.is_admin = True
    db.session.commit()
    click.echo(f"{user.login} is now an administrator.")
