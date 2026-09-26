"""Login throttling: a login is blocked after too many failures within WINDOW.

Two limits work together:
- per login (MAX_FAILURES): guessing one account's password;
- per client IP (MAX_FAILURES_PER_IP): trying many logins from one address.
  The IP is the real client address that ProxyFix takes from nginx.

Failures for non-existent logins are recorded too, so the response
does not reveal whether the login exists.
"""

import math
from datetime import timedelta

from ..extensions import db
from ..models import LoginFailure, utcnow

WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5
# Higher than per login: a club meetup can put many people behind one Wi-Fi address.
MAX_FAILURES_PER_IP = 20


def _wait(condition, limit, now):
    """Seconds until the failures matching the condition drop below the limit, None if they are below."""
    failures = db.session.scalars(
        db.select(LoginFailure.created_at)
        .where(condition, LoginFailure.created_at > now - WINDOW)
        .order_by(LoginFailure.created_at)
    ).all()
    if len(failures) < limit:
        return None
    # Login opens once enough failures leave the window to get below the limit.
    unblocked_at = failures[-limit] + WINDOW
    return max(1, math.ceil((unblocked_at - now).total_seconds()))


def seconds_until_unblocked(login, ip):
    """Seconds to wait until the next attempt, None if neither the login nor the IP is blocked."""
    now = utcnow()
    waits = [
        _wait(LoginFailure.login == login, MAX_FAILURES, now),
        _wait(LoginFailure.ip == ip, MAX_FAILURES_PER_IP, now) if ip else None,
    ]
    waits = [wait for wait in waits if wait is not None]
    return max(waits) if waits else None


def record_failure(login, ip):
    now = utcnow()
    db.session.add(LoginFailure(login=login, ip=ip, created_at=now))
    # Also remove records that no longer affect the block.
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.created_at <= now - WINDOW))
    db.session.commit()


def clear_failures(login):
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.login == login))
    db.session.commit()
