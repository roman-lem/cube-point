from flask import Blueprint, request
from flask_login import current_user

from .auth import auth
from .clubs import clubs
from .errors import ApiError
from .fmc import fmc_bp
from .meetups import meetups
from .series import series_bp

api = Blueprint("api", __name__, url_prefix="/api")
api.register_blueprint(auth)
api.register_blueprint(clubs)
api.register_blueprint(meetups)
api.register_blueprint(series_bp)
api.register_blueprint(fmc_bp)

# Что доступно, пока пользователь не сменил временный пароль.
ALLOWED_BEFORE_PASSWORD_CHANGE = {
    "api.health",
    "api.auth.csrf_token",
    "api.auth.me",
    "api.auth.change_password",
    "api.auth.logout",
}


@api.before_request
def require_password_change():
    if (
        current_user.is_authenticated
        and current_user.must_change_password
        and request.endpoint not in ALLOWED_BEFORE_PASSWORD_CHANGE
    ):
        raise ApiError(403, "password_change_required", "Сначала смените временный пароль")


@api.get("/health")
def health():
    return {"status": "ok"}
