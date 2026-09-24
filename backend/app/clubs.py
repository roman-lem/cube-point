"""Клубы: публичная страница и настройки организатора. Адреса /api/clubs/…"""

from urllib.parse import urlsplit

from flask import Blueprint

from .extensions import db
from .forms import collapse_spaces, get_list, get_str, json_body, raise_if_errors
from .models import CLUB_COLORS, Club, ClubLink, LinkType, Meetup, MeetupStatus
from .permissions import get_membership, get_or_404, is_banned, my_role, require_organizer

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
    live = dict(db.session.execute(
        db.select(Meetup.club_id, Meetup.id).where(Meetup.status == MeetupStatus.LIVE)
    ).all())
    result = []
    for club in db.session.scalars(db.select(Club).order_by(Club.name)):
        membership = get_membership(club.id)
        result.append({
            "id": club.id,
            "name": club.name,
            "city": club.city,
            "logo_color": club.logo_color,
            "my_role": membership.role.value if membership else None,
            "live_meetup_id": live.get(club.id),
        })
    return {"clubs": result}


@clubs.get("/<int:club_id>")
def get_club(club_id):
    club = get_or_404(Club, club_id, "Клуб не найден")
    return {"club": serialize_club(club), "my_role": my_role(club.id), "banned": is_banned(club.id)}


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
    # Ссылки заменяются целиком, порядок — как в запросе.
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
    """Список (тип, url) и ошибки полей вида links.2.url."""
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
    """Ссылка с https:// (если схема не указана) или None, если это не ссылка на сайт."""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or "." not in parts.netloc or " " in url:
        return None
    if len(url) > 500:
        return None
    return url
