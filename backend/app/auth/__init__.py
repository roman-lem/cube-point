"""Login, registration and sessions. Endpoints are in routes.py, routes /api/auth/…"""

from flask import Blueprint

from ..errors import ApiError, error_response
from ..extensions import db, login_manager
from ..models import User

auth = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    # user_id is the string from User.get_id(): "id:session_version".
    # If the version is outdated (password reset or change), the session is invalid.
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


from . import email, routes  # noqa: E402, F401 — registers the endpoints in auth
