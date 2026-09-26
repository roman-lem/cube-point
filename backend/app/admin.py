"""Administration: clubs and their organizers, names of deleted accounts.

Routes /api/admin/…

Administrators only (users.is_admin). Rules: "Roles" in docs/ARCHITECTURE.md.
The first administrator is created with `flask make-admin LOGIN`.
"""

from zoneinfo import available_timezones

import click
from flask import Blueprint, request
from flask.cli import with_appcontext
from flask_login import current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from .auth.validation import login_error, name_error, normalize_login, password_error
from .clubs import text_error
from .errors import ApiError, ValidationError
from .extensions import db
from .forms import collapse_spaces, get_str, json_body, raise_if_errors
from .meetups import iso_utc
from .models import (
    DELETED_USER_NAME, Club, ClubMember, ClubRole, ConsentType, Meetup, MeetupStatus, User,
    UserConsent,
)
from .permissions import is_last_organizer

admin = Blueprint("admin", __name__, url_prefix="/admin")

DEFAULT_TIMEZONE = "Asia/Yekaterinburg"  # Tyumen time
USER_SEARCH_LIMIT = 10


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
    }


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


@admin.get("/users")
def search_users():
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
