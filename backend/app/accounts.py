"""Аккаунты: создание и сброс пароля организатором, удаление аккаунта.

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
from .models import (
    DELETED_USER_NAME, Club, ClubMember, ClubRole, ConsentType, Disqualification, LoginFailure,
    User, UserConsent, utcnow,
)

# Причина дисквалификации удалённого участника: текст организатора мог
# содержать что-то личное, а сама дисквалификация должна остаться.
DELETED_REASON = "Причина удалена вместе с аккаунтом"
from .permissions import is_last_organizer

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


def delete_restriction(user):
    """Почему нельзя удалить аккаунт, или None: последний организатор клуба."""
    clubs = db.session.scalars(
        db.select(Club).join(ClubMember)
        .where(ClubMember.user_id == user.id, ClubMember.role == ClubRole.ORGANIZER)
        .order_by(Club.name)
    ).all()
    names = [f"«{club.name}»" for club in clubs if is_last_organizer(club.id, user.id)]
    if names:
        return f"Сначала передайте роль организатора в клубе {', '.join(names)}"
    return None


def publication_version(user):
    """Версия последнего согласия на распространение или None, если его не давали."""
    return db.session.scalar(
        db.select(UserConsent.version)
        .where(UserConsent.user_id == user.id, UserConsent.type == ConsentType.PUBLICATION)
        .order_by(UserConsent.accepted_at.desc(), UserConsent.id.desc())
        .limit(1)
    )


def delete_account(user, keep_name=False):
    """Удаление аккаунта: персональные данные уничтожаются, результаты остаются.

    Строка users остаётся, на неё ссылаются серии и рекорды: логин, почта,
    хеш пароля и согласия удаляются, имя заменяется на DELETED_USER_NAME.
    С keep_name имя остаётся в результатах и рекордах: вместо согласий
    остаётся одна запись DELETED_NAME с версией последнего согласия на
    распространение (данное согласие не отзывается), проверка — в
    auth.delete_own_account. Публичного профиля у такого аккаунта нет (User.has_profile).
    Человек выходит из всех клубов (вместе с членством удаляется причина
    блокировки), причины дисквалификаций стираются, а сами дисквалификации
    остаются, чтобы аннулированные результаты не вернулись в таблицы.
    Все сессии перестают действовать.
    """
    version = publication_version(user) if keep_name else None
    if keep_name and version is None:
        raise ValueError("Нет согласия на распространение")
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.login == user.login))
    db.session.execute(db.delete(ClubMember).where(ClubMember.user_id == user.id))
    db.session.execute(db.delete(UserConsent).where(UserConsent.user_id == user.id))
    db.session.execute(
        db.update(Disqualification).where(Disqualification.user_id == user.id)
        .values(reason=DELETED_REASON)
    )
    if version is None:
        user.display_name = DELETED_USER_NAME
    else:
        db.session.add(UserConsent(user_id=user.id, type=ConsentType.DELETED_NAME, version=version))
    user.login = None
    user.email = None
    user.email_verified = False
    user.password_hash = None
    user.is_admin = False
    user.must_change_password = False
    user.session_version += 1
    user.deleted_at = utcnow()
