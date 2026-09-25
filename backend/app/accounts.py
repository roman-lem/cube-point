"""Аккаунты, которые создаёт и которым сбрасывает пароль организатор.

Временный пароль показывается один раз и больше нигде не хранится,
при входе с ним нужно сменить пароль (must_change_password).
"""

import secrets

from flask_login import current_user
from werkzeug.security import generate_password_hash

from .auth.validation import login_error, name_error, normalize_login
from .errors import ValidationError
from .extensions import db
from .forms import collapse_spaces, get_str, raise_if_errors
from .models import User

# Без похожих символов (0/O, 1/l/I), чтобы пароль легко было продиктовать.
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PASSWORD_LENGTH = 10


def temporary_password():
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH))


def create_account(data):
    """Новый аккаунт из {"display_name", "login"}: (пользователь, временный пароль)."""
    display_name = collapse_spaces(get_str(data, "display_name"))
    login = normalize_login(get_str(data, "login"))
    raise_if_errors({"display_name": name_error(display_name), "login": login_error(login)})
    if db.session.scalar(db.select(User.id).where(User.login == login)):
        raise ValidationError({"login": "Логин уже занят"})

    password = temporary_password()
    user = User(
        login=login,
        display_name=display_name,
        password_hash=generate_password_hash(password),
        must_change_password=True,
        created_by=current_user.id,
    )
    db.session.add(user)
    db.session.flush()
    return user, password


def reset_password(user):
    """Временный пароль вместо текущего. Все сессии пользователя перестают действовать."""
    password = temporary_password()
    user.password_hash = generate_password_hash(password)
    user.must_change_password = True
    user.session_version += 1
    return password
