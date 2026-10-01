"""Password reset by email, routes /api/auth/password-reset…

- The user enters a login or an email. If the account has a confirmed email,
  a letter with a link goes there. The response is the same in every case and the
  letter is sent in the background (mail.send_later), so neither the response nor
  its time reveals whether the account exists and has an email.
- The link works once, for LINK_LIFETIME, and only the latest one: a new letter
  and a password set by any link cancel the earlier ones. The link also stops
  working if the account's email has changed since the letter.
- Opening the link and setting a new password logs the user in; other sessions end,
  and a notification goes to the email.
- Requests are limited per client IP (429, generous: a meetup is one Wi-Fi address)
  and per account. Over the account limit the letter is silently not sent:
  a different response would reveal that the account exists.
"""

import math
import secrets
from datetime import timedelta

from flask import current_app, request
from werkzeug.security import generate_password_hash

from .. import mail
from ..errors import ApiError
from ..extensions import db
from ..forms import get_str, json_body, raise_if_errors
from ..models import PasswordReset, User, utcnow
from . import auth, throttle
from .email import site_name, token_hash
from .routes import serialize_user, start_session
from .validation import EMAIL_MAX, new_password_error, normalize_email, normalize_login

LINK_LIFETIME = timedelta(hours=1)

# Rate limits: (number of requests, window).
USER_LIMITS = [(1, timedelta(minutes=1)), (5, timedelta(hours=1))]
IP_LIMITS = [(30, timedelta(hours=1))]
# Older rows affect neither limits nor links and are deleted.
KEEP = timedelta(days=2)


def find_user(login_or_email):
    """The account by login or by confirmed email (with "@"). Deleted accounts have neither."""
    if "@" in login_or_email:
        return db.session.scalar(db.select(User).where(User.email == normalize_email(login_or_email)))
    return db.session.scalar(db.select(User).where(User.login == normalize_login(login_or_email)))


def _wait(condition, limits, now):
    """Seconds until a request is allowed under the limits, None if it is allowed now."""
    waits = []
    for limit, window in limits:
        sent = db.session.scalars(
            db.select(PasswordReset.created_at)
            .where(condition, PasswordReset.created_at > now - window)
            .order_by(PasswordReset.created_at)
        ).all()
        if len(sent) >= limit:
            allowed_at = sent[-limit] + window
            waits.append(max(1, math.ceil((allowed_at - now).total_seconds())))
    return max(waits) if waits else None


def check_ip_limit(ip, now):
    wait = ip and _wait(PasswordReset.ip == ip, IP_LIMITS, now)
    if not wait:
        return
    when = f"{wait} сек." if wait < 60 else f"{-(-wait // 60)} мин."
    raise ApiError(
        429, "too_many_requests",
        f"Слишком много запросов. Попробуйте через {when}",
        extra={"retry_after": wait},
        headers={"Retry-After": str(wait)},
    )


def user_limit_reached(user, now):
    # Only requests with a letter count: someone else's requests over the limit
    # must not keep the owner without letters.
    condition = (PasswordReset.user_id == user.id) & PasswordReset.token_hash.is_not(None)
    return _wait(condition, USER_LIMITS, now) is not None


def cancel_open(user, now):
    db.session.execute(
        db.update(PasswordReset)
        .where(
            PasswordReset.user_id == user.id,
            PasswordReset.token_hash.is_not(None),
            PasswordReset.used_at.is_(None),
            PasswordReset.cancelled_at.is_(None),
        )
        .values(cancelled_at=now)
    )


def reset_letter(user, link):
    return (
        "Восстановление пароля",
        f"Здравствуйте, {user.display_name}!\n\n"
        f"Кто-то запросил восстановление пароля вашего аккаунта на сайте {site_name()} "
        f"(логин: {user.login}). Чтобы задать новый пароль, откройте ссылку:\n\n{link}\n\n"
        "Ссылка действует 1 час. Если вы не запрашивали восстановление, просто "
        "проигнорируйте письмо: пароль останется прежним.\n",
    )


def changed_letter(user):
    return (
        "Пароль вашего аккаунта был изменён",
        f"Здравствуйте, {user.display_name}!\n\n"
        f"Пароль вашего аккаунта на сайте {site_name()} был изменён по ссылке "
        "из письма для восстановления пароля. Вход на других устройствах завершён.\n\n"
        "Если это были не вы, напишите разработчику (контакты — внизу страниц сайта).\n",
    )


@auth.post("/password-reset")
def request_password_reset():
    login_or_email = get_str(json_body(), "login_or_email").strip()[:EMAIL_MAX]
    raise_if_errors({"login_or_email": None if login_or_email else "Введите логин или почту"})

    now = utcnow()
    ip = request.remote_addr
    check_ip_limit(ip, now)

    user = find_user(login_or_email)
    reset = PasswordReset(user_id=user and user.id, ip=ip, created_at=now)
    if user and user.email and not user_limit_reached(user, now):
        token = secrets.token_urlsafe(32)
        # The token is in the fragment: the browser never sends it to the server
        # (request line, Referer), so it stays out of nginx logs. The page posts it.
        link = f"{current_app.config['SITE_URL']}/reset-password#token={token}"
        cancel_open(user, now)
        reset.token_hash = token_hash(token)
        reset.email = user.email
        mail.send_later(user.email, *reset_letter(user, link))
    db.session.add(reset)
    db.session.execute(db.delete(PasswordReset).where(PasswordReset.created_at <= now - KEEP))
    db.session.commit()
    return {}


def valid_reset(token):
    """The open link's request with its user, or an error why the link does not work."""
    reset = token and db.session.scalar(
        db.select(PasswordReset).where(PasswordReset.token_hash == token_hash(token))
    )
    if not reset:
        raise ApiError(404, "link_invalid", "Ссылка недействительна")
    if reset.used_at is not None:
        raise ApiError(410, "link_used", "Ссылка уже использована")
    if reset.cancelled_at is not None:
        raise ApiError(
            410, "link_cancelled",
            "Ссылка больше не действует: отправлена новая ссылка или пароль уже изменён",
        )
    if reset.created_at + LINK_LIFETIME <= utcnow():
        raise ApiError(410, "link_expired", "Ссылка устарела. Запросите новую")
    user = db.session.get(User, reset.user_id)
    if user.email != reset.email:
        raise ApiError(410, "link_cancelled", "Ссылка больше не действует: почта аккаунта изменилась")
    return reset, user


@auth.post("/password-reset/check")
def check_password_reset():
    """Opening the link: whether it works, and the login (the user may have forgotten it,
    and whoever opened the link has the mailbox)."""
    _, user = valid_reset(get_str(json_body(), "token"))
    return {"login": user.login}


@auth.post("/password-reset/confirm")
def confirm_password_reset():
    data = json_body()
    reset, user = valid_reset(get_str(data, "token"))
    new_password = get_str(data, "new_password")
    raise_if_errors({
        "new_password": new_password_error(new_password, user.login, user.password_hash),
    })

    now = utcnow()
    user.password_hash = generate_password_hash(new_password)
    user.must_change_password = False
    # All other sessions and remember cookies stop working.
    user.session_version += 1
    reset.used_at = now
    cancel_open(user, now)
    db.session.commit()
    # If the login was locked out by throttling, the new password works right away.
    throttle.clear_failures(user.login)

    mail.send_later(user.email, *changed_letter(user))
    start_session(user, remember=False)
    return {"user": serialize_user(user)}
