"""Club roles and permission checks. All permission checks are server-side only."""

from flask_login import current_user

from .errors import ApiError
from .extensions import db
from .models import ClubMember, ClubRole
from .pledge import PLEDGE_TEXT, PLEDGE_VERSION, pledge_accepted


def get_or_404(model, object_id, message="Не найдено"):
    obj = db.session.get(model, object_id)
    if obj is None:
        raise ApiError(404, "not_found", message)
    return obj


def get_membership(club_id, user=None):
    """Club membership of the user (current by default), or None."""
    user = user or current_user
    if not user.is_authenticated:
        return None
    return db.session.get(ClubMember, (club_id, user.id))


def my_role(club_id):
    """Role of the current user in the club: "organizer", "member" or None."""
    membership = get_membership(club_id)
    return membership.role.value if membership else None


def is_banned(club_id, user=None):
    membership = get_membership(club_id, user)
    return membership is not None and membership.banned_at is not None


def is_organizer(club_id):
    """The organizer role, whether or not the pledge is accepted."""
    membership = get_membership(club_id)
    return membership is not None and membership.role == ClubRole.ORGANIZER


def is_active_organizer(club_id):
    """An organizer who has accepted the pledge: only they get the organizer tools and data."""
    return is_organizer(club_id) and pledge_accepted(club_id, current_user)


def pending_pledge(club_id):
    """The pledge to show to an organizer who has not accepted it yet, otherwise None."""
    if is_organizer(club_id) and not pledge_accepted(club_id, current_user):
        return {"version": PLEDGE_VERSION, "text": PLEDGE_TEXT}
    return None


def require_organizer(club_id):
    if not current_user.is_authenticated:
        raise ApiError(401, "unauthorized", "Нужно войти")
    if not is_organizer(club_id):
        raise ApiError(403, "forbidden", "Это может только организатор клуба")
    if not pledge_accepted(club_id, current_user):
        raise ApiError(
            403, "pledge_required", "Сначала примите обязательство организатора на странице клуба",
        )


def require_club_manager(club_id):
    """Managing club members: a club organizer or the administrator."""
    if not current_user.is_authenticated:
        raise ApiError(401, "unauthorized", "Нужно войти")
    if not current_user.is_admin:
        require_organizer(club_id)


def require_not_banned(club_id):
    """A banned user stops submitting attempts immediately, including at a live meetup."""
    if is_banned(club_id):
        raise ApiError(403, "banned", "Вы заблокированы в этом клубе")


def is_last_organizer(club_id, user_id):
    organizers = db.session.scalars(db.select(ClubMember.user_id).where(
        ClubMember.club_id == club_id, ClubMember.role == ClubRole.ORGANIZER,
    )).all()
    return organizers == [user_id]
