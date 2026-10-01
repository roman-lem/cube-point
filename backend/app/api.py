from flask import Blueprint, request
from flask_login import current_user

from .admin import admin
from .auth import auth
from .clubs import clubs
from .consents import consents_required
from .desk import desk
from .errors import ApiError
from .fmc import fmc_bp
from .meetups import meetups
from .members import members
from .profiles import profiles
from .series import series_bp

api = Blueprint("api", __name__, url_prefix="/api")
api.register_blueprint(auth)
api.register_blueprint(clubs)
api.register_blueprint(members)
api.register_blueprint(profiles)
api.register_blueprint(meetups)
api.register_blueprint(series_bp)
api.register_blueprint(fmc_bp)
api.register_blueprint(desk)
api.register_blueprint(admin)

# What is available while the user has not changed the temporary password.
ALLOWED_BEFORE_PASSWORD_CHANGE = {
    "api.health",
    "api.auth.csrf_token",
    "api.auth.me",
    "api.auth.change_password",
    "api.auth.logout",
    # Do not need a login: the link from the letter may be opened in a logged-in browser.
    "api.auth.request_password_reset",
    "api.auth.check_password_reset",
    "api.auth.confirm_password_reset",
}


# What is available while the user has not given the current consents:
# the only way to refuse them is to delete the account.
ALLOWED_BEFORE_CONSENTS = ALLOWED_BEFORE_PASSWORD_CHANGE | {
    "api.auth.accept_consents",
    "api.auth.delete_own_account",
}


@api.before_request
def require_password_change():
    if (
        current_user.is_authenticated
        and current_user.must_change_password
        and request.endpoint not in ALLOWED_BEFORE_PASSWORD_CHANGE
    ):
        raise ApiError(403, "password_change_required", "Сначала смените временный пароль")


@api.before_request
def require_consents():
    if (
        current_user.is_authenticated
        and request.endpoint not in ALLOWED_BEFORE_CONSENTS
        and consents_required(current_user)
    ):
        raise ApiError(403, "consents_required", "Сначала дайте согласие на обработку данных")


@api.get("/health")
def health():
    return {"status": "ok"}
