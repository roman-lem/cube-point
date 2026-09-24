"""Вход, регистрация и сессии. Эндпоинты — в routes.py, адреса /api/auth/…"""

from flask import Blueprint

from ..errors import ApiError, error_response
from ..extensions import db, login_manager
from ..models import User

auth = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    # user_id — строка из User.get_id(): "id:session_version".
    # Если версия устарела (сброс или смена пароля), сессия не действует.
    id_part, _, version = user_id.partition(":")
    if not (id_part.isdigit() and version.isdigit()):
        return None
    user = db.session.get(User, int(id_part))
    if user is None or user.session_version != int(version):
        return None
    return user


@login_manager.unauthorized_handler
def unauthorized():
    return error_response(ApiError(401, "unauthorized", "Нужно войти"))


from . import routes  # noqa: E402, F401 — регистрирует эндпоинты в auth
