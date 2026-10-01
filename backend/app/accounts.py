"""Accounts: creation and password reset by an organizer, account deletion.

A temporary password is shown once and is not stored anywhere else;
after logging in with it the user must change it (must_change_password).
"""

import secrets

from flask_login import current_user
from werkzeug.security import generate_password_hash

from .auth.validation import login_error, name_error, normalize_login
from .errors import ValidationError
from .extensions import db
from .forms import collapse_spaces, get_str, raise_if_errors
from .models import (
    DELETED_USER_NAME, Club, ClubMember, ClubRole, ConsentType, Disqualification, DisplayNameChange,
    EmailConfirmation, LoginFailure, PasswordReset, User, UserConsent, utcnow,
)

# Disqualification reason for a deleted user: the organizer's text might
# contain something personal, while the disqualification itself must stay.
DELETED_REASON = "Причина удалена вместе с аккаунтом"
from .permissions import is_last_organizer

# No look-alike characters (0/O, 1/l/I), so the password is easy to dictate.
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PASSWORD_LENGTH = 10


def temporary_password():
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH))


def create_account(data):
    """New account from {"display_name", "login"}: (user, temporary password)."""
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
    """Replaces the password with a temporary one. All of the user's sessions stop working."""
    password = temporary_password()
    user.password_hash = generate_password_hash(password)
    user.must_change_password = True
    user.session_version += 1
    return password


def delete_restriction(user):
    """Why the account cannot be deleted, or None: the last organizer of a club."""
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
    """Version of the latest publication consent, or None if it was never given."""
    return db.session.scalar(
        db.select(UserConsent.version)
        .where(UserConsent.user_id == user.id, UserConsent.type == ConsentType.PUBLICATION)
        .order_by(UserConsent.accepted_at.desc(), UserConsent.id.desc())
        .limit(1)
    )


def delete_account(user, keep_name=False):
    """Account deletion: personal data is destroyed, results stay.

    The users row stays because series and records reference it: login, email,
    password hash, consents, email and password reset letters and the name history are deleted, the name becomes DELETED_USER_NAME.
    With keep_name the name stays in results and records: instead of the consents
    a single DELETED_NAME entry remains with the version of the latest
    publication consent (that consent is not withdrawn); the check is in
    auth.delete_own_account. Such an account has no public profile (User.has_profile).
    The user leaves all clubs (the ban reason goes away together with
    the membership), disqualification reasons are erased, but the disqualifications
    themselves stay so the annulled results do not come back to the tables.
    All sessions stop working.
    """
    version = publication_version(user) if keep_name else None
    if keep_name and version is None:
        raise ValueError("Нет согласия на распространение")
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.login == user.login))
    db.session.execute(db.delete(ClubMember).where(ClubMember.user_id == user.id))
    db.session.execute(db.delete(UserConsent).where(UserConsent.user_id == user.id))
    db.session.execute(db.delete(EmailConfirmation).where(EmailConfirmation.user_id == user.id))
    db.session.execute(db.delete(PasswordReset).where(PasswordReset.user_id == user.id))
    # Former names are personal data too.
    db.session.execute(db.delete(DisplayNameChange).where(DisplayNameChange.user_id == user.id))
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
    user.password_hash = None
    user.is_admin = False
    user.must_change_password = False
    user.session_version += 1
    user.deleted_at = utcnow()
