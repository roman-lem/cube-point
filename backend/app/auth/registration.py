"""Protection of registration from scripts, without external services.

- A bot trap: the form has a hidden field (TRAP_FIELD) that people do not see
  and leave empty. A filled one means a script.
- Minimum fill time: GET /api/auth/registration gives a signed form token with
  the moment it was issued. A request sooner than MIN_FILL_TIME after it, or with
  a missing, forged or stale token, is rejected. The moment comes from the server,
  so the client cannot fake it.
  These two are rejected without saying why.
- Per IP: IP_HOURLY_LIMIT registrations per hour and IP_DAILY_LIMIT per day,
  generous for a meetup where newcomers sign up from one Wi-Fi address.
- A fuse: more than TOTAL_HOURLY_LIMIT registrations per hour from all addresses
  closes registration for a while and writes a warning to the log.

Successful registrations go to the registrations journal (the IP is not stored
in users), records older than a day are removed.
"""

from datetime import datetime, timedelta, timezone

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer

from ..errors import ApiError
from ..extensions import db
from ..models import Registration, utcnow

TRAP_FIELD = "website"
MIN_FILL_TIME = timedelta(seconds=3)
# A form open longer has to be reloaded: one token is not reused forever.
MAX_FORM_AGE = timedelta(days=1)

IP_HOURLY_LIMIT = 30
IP_DAILY_LIMIT = 60
TOTAL_HOURLY_LIMIT = 200
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def _serializer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="registration-form")


def form_token(now=None):
    issued_at = (now or utcnow()).replace(tzinfo=timezone.utc).timestamp()
    return _serializer().dumps(issued_at)


def _form_issued_at(token):
    if not isinstance(token, str) or not token:
        return None
    try:
        issued_at = _serializer().loads(token)
    except BadSignature:
        return None
    if not isinstance(issued_at, (int, float)):
        return None
    return datetime.fromtimestamp(issued_at, timezone.utc).replace(tzinfo=None)


def check_form(data, now):
    """Rejects requests from scripts: a filled trap field or a form filled too fast."""
    issued_at = _form_issued_at(data.get("form_token"))
    if (
        data.get(TRAP_FIELD)
        or issued_at is None
        or now - issued_at < MIN_FILL_TIME
        or now - issued_at > MAX_FORM_AGE
    ):
        raise ApiError(
            400, "registration_rejected",
            "Не удалось зарегистрироваться. Обновите страницу и попробуйте ещё раз",
        )


def _count(condition, since):
    return db.session.scalar(
        db.select(db.func.count(Registration.id)).where(condition, Registration.created_at > since)
    )


def check_limits(ip, now):
    if _count(Registration.ip == ip, now - HOUR) >= IP_HOURLY_LIMIT or \
            _count(Registration.ip == ip, now - DAY) >= IP_DAILY_LIMIT:
        raise ApiError(
            429, "too_many_registrations",
            "Слишком много регистраций с этого адреса. Попробуйте позже",
        )
    if _count(db.true(), now - HOUR) >= TOTAL_HOURLY_LIMIT:
        current_app.logger.warning(
            "Registration fuse: more than %s registrations in the last hour", TOTAL_HOURLY_LIMIT,
        )
        raise ApiError(503, "registration_unavailable", "Регистрация временно недоступна")


def record(ip, now):
    """Adds the registration to the journal; committed together with the new user."""
    db.session.add(Registration(ip=ip, created_at=now))
    db.session.execute(db.delete(Registration).where(Registration.created_at <= now - DAY))
