"""Роли в клубе и проверки прав. Все проверки прав — только на сервере."""

from flask_login import current_user

from .errors import ApiError
from .extensions import db
from .models import ClubMember, ClubRole


def get_or_404(model, object_id, message="Не найдено"):
    obj = db.session.get(model, object_id)
    if obj is None:
        raise ApiError(404, "not_found", message)
    return obj


def get_membership(club_id, user=None):
    """Членство пользователя (по умолчанию текущего) в клубе или None."""
    user = user or current_user
    if not user.is_authenticated:
        return None
    return db.session.get(ClubMember, (club_id, user.id))


def my_role(club_id):
    """Роль текущего пользователя в клубе: "organizer", "member" или None."""
    membership = get_membership(club_id)
    return membership.role.value if membership else None


def is_banned(club_id, user=None):
    membership = get_membership(club_id, user)
    return membership is not None and membership.banned_at is not None


def is_organizer(club_id):
    membership = get_membership(club_id)
    return membership is not None and membership.role == ClubRole.ORGANIZER


def require_organizer(club_id):
    if not current_user.is_authenticated:
        raise ApiError(401, "unauthorized", "Нужно войти")
    if not is_organizer(club_id):
        raise ApiError(403, "forbidden", "Это может только организатор клуба")
