"""Login throttling: at most MAX_FAILURES failures per login within WINDOW.

Counted by login only: simpler, and enough for a club service.
Failures for non-existent logins are recorded too, so the response
does not reveal whether the login exists.
"""

import math
from datetime import timedelta

from ..extensions import db
from ..models import LoginFailure, utcnow

WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5


def seconds_until_unblocked(login):
    """Seconds to wait until the next attempt, None if login is not blocked."""
    now = utcnow()
    failures = db.session.scalars(
        db.select(LoginFailure.created_at)
        .where(LoginFailure.login == login, LoginFailure.created_at > now - WINDOW)
        .order_by(LoginFailure.created_at)
    ).all()
    if len(failures) < MAX_FAILURES:
        return None
    # Login opens once enough failures leave the window to get below the limit.
    unblocked_at = failures[-MAX_FAILURES] + WINDOW
    return max(1, math.ceil((unblocked_at - now).total_seconds()))


def record_failure(login):
    now = utcnow()
    db.session.add(LoginFailure(login=login, created_at=now))
    # Also remove records that no longer affect the block.
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.created_at <= now - WINDOW))
    db.session.commit()


def clear_failures(login):
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.login == login))
    db.session.commit()
