"""Clubs: public page and organizer settings. Routes /api/clubs/…"""

from urllib.parse import urlsplit

from flask import Blueprint
from flask_login import current_user

from .errors import ApiError
from .extensions import db
from .forms import collapse_spaces, get_list, get_str, json_body, raise_if_errors
from .models import (
    CLUB_COLORS, Club, ClubLink, ClubMember, LinkType, Meetup, MeetupStatus,
)
from .permissions import (
    get_membership, get_or_404, is_banned, is_organizer, my_role, pending_pledge, require_organizer,
)
from .pledge import PLEDGE_VERSION, pledge_accepted, record_pledge

clubs = Blueprint("clubs", __name__, url_prefix="/clubs")

MAX_LINKS = 10


def serialize_club(club):
    return {
        "id": club.id,
        "name": club.name,
        "city": club.city,
        "timezone": club.timezone,
        "description": club.description,
        "logo_color": club.logo_color,
        "links": [{"type": link.type.value, "url": link.url} for link in club.links],
    }


@clubs.get("")
def list_clubs():
    """All clubs, those with the most recent meetups first (landing and clubs page)."""
    live = dict(db.session.execute(
        db.select(Meetup.club_id, Meetup.id).where(Meetup.status == MeetupStatus.LIVE)
    ).all())
    # Members exclude banned ones, as in the public club member list.
    member_counts = dict(db.session.execute(
        db.select(ClubMember.club_id, db.func.count())
        .where(ClubMember.banned_at.is_(None))
        .group_by(ClubMember.club_id)
    ).all())
    # Only started and finished meetups count, planned ones do not.
    meetup_stats = {
        club_id: (count, last_date)
        for club_id, count, last_date in db.session.execute(
            db.select(Meetup.club_id, db.func.count(), db.func.max(Meetup.date))
            .where(Meetup.status != MeetupStatus.PLANNED)
            .group_by(Meetup.club_id)
        )
    }
    result = []
    for club in db.session.scalars(db.select(Club).order_by(Club.name)):
        membership = get_membership(club.id)
        meetup_count, last_date = meetup_stats.get(club.id, (0, None))
        result.append({
            "id": club.id,
            "name": club.name,
            "city": club.city,
            "logo_color": club.logo_color,
            # A banned member is not counted as a member ("My clubs" in the profile).
            "my_role": (
                membership.role.value if membership and not membership.banned_at else None
            ),
            "live_meetup_id": live.get(club.id),
            "member_count": member_counts.get(club.id, 0),
            "meetup_count": meetup_count,
            # The meetup date is already in the club's time zone.
            "last_meetup_date": last_date.isoformat() if last_date else None,
        })
    # Recent meetups first, clubs without meetups last; ties by name
    # (the sort is stable and the source list is already sorted by name).
    result.sort(key=lambda c: c["last_meetup_date"] or "", reverse=True)
    return {"clubs": result}


@clubs.get("/<int:club_id>")
def get_club(club_id):
    club = get_or_404(Club, club_id, "Клуб не найден")
    return {
        "club": serialize_club(club),
        "my_role": my_role(club.id),
        "banned": is_banned(club.id),
        # Organizer tools stay closed until the pledge is accepted (pledge.py).
        "pledge": pending_pledge(club.id),
    }


@clubs.post("/<int:club_id>/organizer-pledge")
def accept_pledge(club_id):
    """The organizer accepts the pledge. Request body: {"version"} of the text displayed."""
    club = get_or_404(Club, club_id, "Клуб не найден")
    if not current_user.is_authenticated:
        raise ApiError(401, "unauthorized", "Нужно войти")
    if not is_organizer(club.id):
        raise ApiError(403, "forbidden", "Это может только организатор клуба")
    if json_body().get("version") != PLEDGE_VERSION:
        raise ApiError(409, "pledge_outdated", "Текст обязательства обновился, обновите страницу")
    if not pledge_accepted(club.id, current_user):
        record_pledge(club.id, current_user)
        db.session.commit()
    return "", 204


@clubs.patch("/<int:club_id>")
def update_club(club_id):
    club = get_or_404(Club, club_id, "Клуб не найден")
    require_organizer(club.id)

    data = json_body()
    name = collapse_spaces(get_str(data, "name"))
    city = collapse_spaces(get_str(data, "city"))
    description = get_str(data, "description").strip()
    logo_color = get_str(data, "logo_color")

    errors = {
        "name": text_error(name, 100, "Введите название"),
        "city": text_error(city, 100, "Введите город"),
        "description": "Максимум 2000 символов" if len(description) > 2000 else None,
        "logo_color": None if logo_color in CLUB_COLORS else "Выберите цвет из списка",
    }
    links, link_errors = parse_links(get_list(data, "links"))
    errors.update(link_errors)
    raise_if_errors(errors)

    club.name = name
    club.city = city
    club.description = description or None
    club.logo_color = logo_color
    # Links are replaced as a whole, in the order of the request.
    club.links = [
        ClubLink(type=link_type, url=url, position=position)
        for position, (link_type, url) in enumerate(links)
    ]
    db.session.commit()
    return {"club": serialize_club(club)}


def text_error(value, max_length, empty_message):
    if not value:
        return empty_message
    if len(value) > max_length:
        return f"Максимум {max_length} символов"
    return None


def parse_links(items):
    """List of (type, url) and field errors like links.2.url."""
    links, errors = [], {}
    if len(items) > MAX_LINKS:
        errors["links"] = f"Не больше {MAX_LINKS} ссылок"
        return links, errors
    for index, item in enumerate(items):
        item = item if isinstance(item, dict) else {}
        link_type = get_str(item, "type")
        url = normalize_url(get_str(item, "url"))
        if link_type not in LinkType:
            errors[f"links.{index}.type"] = "Неизвестный тип ссылки"
        elif url is None:
            errors[f"links.{index}.url"] = "Неверная ссылка"
        else:
            links.append((LinkType(link_type), url))
    return links, errors


def normalize_url(url):
    """URL with https:// (if no scheme is given), or None if it is not a website link."""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or "." not in parts.netloc or " " in url:
        return None
    if len(url) > 500:
        return None
    return url
