"""Binding an email with confirmation, routes /api/auth/email…

- The user enters an address and gets a letter with a link. The address is bound
  (users.email) only after the link is opened: until then it is pending, and a
  confirmed address stays the old one. The link works once, for LINK_LIFETIME,
  and only the latest letter's link works.
- One address belongs to one account. If it belongs to another one, the response
  is the same, and the letter says that the address is already bound, without a link:
  neither the response nor its time reveals someone else's address.
- Letters are limited per user and per client IP, so the site cannot be used to send spam.
- Binding a new address and removing one need the current password: otherwise
  whoever got hold of an unlocked phone binds their address and takes the account
  over through password recovery. Sending the letter again to the pending address
  does not: that address was confirmed with the password.
"""

import hashlib
import math
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from flask import current_app, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from .. import mail
from ..errors import ApiError, ValidationError
from ..extensions import db
from ..forms import get_str, json_body, raise_if_errors
from ..models import EmailConfirmation, User, utcnow
from . import auth
from .validation import email_error, normalize_email

LINK_LIFETIME = timedelta(hours=24)

# Rate limits: (number of letters, window). Per IP it is generous:
# at a meetup many people go online through one Wi-Fi address.
USER_LIMITS = [(1, timedelta(minutes=1)), (5, timedelta(hours=1))]
IP_LIMITS = [(30, timedelta(hours=1))]
# Closed rows older than this affect neither limits nor links and are deleted.
KEEP_CLOSED = timedelta(days=2)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def pending_confirmation(user):
    """The open letter of the user: the address waiting for confirmation, or None."""
    return db.session.scalar(
        db.select(EmailConfirmation)
        .where(
            EmailConfirmation.user_id == user.id,
            EmailConfirmation.used_at.is_(None),
            EmailConfirmation.cancelled_at.is_(None),
        )
        .order_by(EmailConfirmation.created_at.desc(), EmailConfirmation.id.desc())
        .limit(1)
    )


def email_state(user):
    """The user's email fields (in /me and in the responses here): the confirmed address
    and the pending one with whether its link has expired."""
    pending = pending_confirmation(user)
    return {
        "email": user.email,
        "pending_email": pending and {
            "address": pending.email,
            "expired": pending.created_at + LINK_LIFETIME <= utcnow(),
        },
    }


def cancel_pending(user, now):
    db.session.execute(
        db.update(EmailConfirmation)
        .where(
            EmailConfirmation.user_id == user.id,
            EmailConfirmation.used_at.is_(None),
            EmailConfirmation.cancelled_at.is_(None),
        )
        .values(cancelled_at=now)
    )


def _wait(condition, limits, now):
    """Seconds until a letter is allowed under the limits, None if it is allowed now."""
    waits = []
    for limit, window in limits:
        sent = db.session.scalars(
            db.select(EmailConfirmation.created_at)
            .where(condition, EmailConfirmation.created_at > now - window)
            .order_by(EmailConfirmation.created_at)
        ).all()
        if len(sent) >= limit:
            allowed_at = sent[-limit] + window
            waits.append(max(1, math.ceil((allowed_at - now).total_seconds())))
    return max(waits) if waits else None


def check_limits(user, ip, now):
    waits = [_wait(EmailConfirmation.user_id == user.id, USER_LIMITS, now)]
    if ip:
        waits.append(_wait(EmailConfirmation.ip == ip, IP_LIMITS, now))
    waits = [wait for wait in waits if wait is not None]
    if not waits:
        return
    wait = max(waits)
    when = f"{wait} сек." if wait < 60 else f"{-(-wait // 60)} мин."
    raise ApiError(
        429, "too_many_letters",
        f"Слишком много писем. Попробуйте через {when}",
        extra={"retry_after": wait},
        headers={"Retry-After": str(wait)},
    )


def site_name():
    """The site address for letters: the service name lives only in the frontend."""
    return urlsplit(current_app.config["SITE_URL"]).netloc


def confirmation_letter(user, link):
    return (
        "Подтвердите почту",
        f"Здравствуйте, {user.display_name}!\n\n"
        f"Чтобы привязать эту почту к вашему аккаунту на сайте {site_name()}, "
        f"откройте ссылку:\n\n{link}\n\n"
        "Ссылка действует 24 часа. Если вы не указывали эту почту, просто "
        "проигнорируйте письмо.\n",
    )


def taken_letter():
    return (
        "Ваша почта уже привязана",
        f"Здравствуйте!\n\nЭтот адрес указали в настройках аккаунта на сайте {site_name()}, "
        "но он уже привязан к другому аккаунту, поэтому привязать его ещё раз нельзя.\n\n"
        "Если это были вы, войдите в аккаунт, к которому привязана эта почта. "
        "Если нет, просто проигнорируйте письмо.\n",
    )


def changed_letter(user):
    return (
        "Почта аккаунта изменена",
        f"Здравствуйте, {user.display_name}!\n\n"
        f"Почта вашего аккаунта на сайте {site_name()} изменена на другой адрес. "
        "Письма теперь будут приходить туда.\n\n"
        "Если это сделали не вы, войдите на сайт, смените пароль и напишите разработчику "
        "(контакты — внизу страниц сайта).\n",
    )


@auth.post("/email")
@login_required
def request_email():
    """Sends a confirmation letter to a new address (with the password); again for the pending one."""
    data = json_body()
    email = normalize_email(get_str(data, "email"))
    user = current_user._get_current_object()
    pending = pending_confirmation(user)
    resend = pending is not None and pending.email == email
    raise_if_errors({
        "email": email_error(email),
        "password": None if resend else password_error(user, get_str(data, "password")),
    })
    if email == user.email:
        raise ValidationError({"email": "Эта почта уже привязана к вашему аккаунту"})

    now = utcnow()
    ip = request.remote_addr
    check_limits(user, ip, now)

    taken = db.session.scalar(db.select(User.id).where(User.email == email, User.id != user.id))
    token = None
    if taken:
        subject, body = taken_letter()
    else:
        token = secrets.token_urlsafe(32)
        # The token is in the fragment: the browser never sends it to the server
        # (request line, Referer), so it stays out of nginx logs. The page posts it.
        link = f"{current_app.config['SITE_URL']}/confirm-email#token={token}"
        subject, body = confirmation_letter(user, link)

    confirmation = EmailConfirmation(
        user_id=user.id, email=email, token_hash=token and token_hash(token),
        ip=ip, created_at=now,
    )
    try:
        mail.send(email, subject, body)
    except mail.MailError:
        # The failed letter still counts for the limits, but the address is not pending.
        confirmation.cancelled_at = now
        db.session.add(confirmation)
        db.session.commit()
        raise ApiError(
            503, "mail_failed", "Не удалось отправить письмо. Попробуйте позже",
        )

    cancel_pending(user, now)
    db.session.add(confirmation)
    db.session.execute(
        db.delete(EmailConfirmation).where(
            EmailConfirmation.created_at <= now - KEEP_CLOSED,
            (EmailConfirmation.used_at.is_not(None)) | (EmailConfirmation.cancelled_at.is_not(None)),
        )
    )
    db.session.commit()
    return email_state(user)


@auth.delete("/email/pending")
@login_required
def cancel_pending_email():
    cancel_pending(current_user, utcnow())
    db.session.commit()
    return email_state(current_user)


@auth.post("/email/confirm")
def confirm_email():
    """Opening the link from the letter. No login needed: the link is often opened
    on another device. The token alone proves access to the mailbox."""
    token = get_str(json_body(), "token")
    confirmation = token and db.session.scalar(
        db.select(EmailConfirmation).where(EmailConfirmation.token_hash == token_hash(token))
    )
    if not confirmation:
        raise ApiError(404, "link_invalid", "Ссылка недействительна")
    if confirmation.used_at is not None:
        raise ApiError(410, "link_used", "Ссылка уже использована")
    if confirmation.cancelled_at is not None:
        raise ApiError(
            410, "link_cancelled",
            "Ссылка больше не действует: адрес изменили или отправили новое письмо",
        )
    now = utcnow()
    if confirmation.created_at + LINK_LIFETIME <= now:
        raise ApiError(410, "link_expired", "Ссылка устарела. Отправьте письмо ещё раз в настройках профиля")

    # The address could have been bound to another account after the letter was sent.
    # Whoever opened the link has the mailbox, so telling them reveals nothing.
    taken = db.session.scalar(
        db.select(User.id).where(User.email == confirmation.email, User.id != confirmation.user_id)
    )
    if taken:
        confirmation.cancelled_at = now
        db.session.commit()
        raise ApiError(409, "email_taken", "Этот адрес уже привязан к другому аккаунту")

    user = db.session.get(User, confirmation.user_id)
    old_email = user.email
    user.email = confirmation.email
    confirmation.used_at = now
    try:
        db.session.commit()
    except IntegrityError:
        # Another account confirmed the same address at the same moment.
        db.session.rollback()
        raise ApiError(409, "email_taken", "Этот адрес уже привязан к другому аккаунту")

    # The previous address learns about the change: protection against account takeover.
    # The address is already changed, so a failed letter is only logged (by mail.send).
    if old_email:
        try:
            mail.send(old_email, *changed_letter(user))
        except mail.MailError:
            pass
    return {"email": user.email}


def password_error(user, password):
    if not password:
        return "Введите пароль"
    if not check_password_hash(user.password_hash, password):
        return "Неверный пароль"
    return None


@auth.post("/email/remove")
@login_required
def remove_email():
    user = current_user._get_current_object()
    raise_if_errors({"password": password_error(user, get_str(json_body(), "password"))})
    user.email = None
    db.session.commit()
    return email_state(user)
