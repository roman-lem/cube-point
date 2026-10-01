"""Login throttling by failed attempts (login_failures).

Three limits work together:
- per pair (login, IP), PAIR_LIMIT in PAIR_WINDOW: whoever mistypes is blocked
  only for that login and only from their address;
- per login from all addresses, LOGIN_LIMIT in LONG_WINDOW: guessing one
  account's password from many addresses; the owner's typos do not reach it;
- per IP, IP_LOGINS_LIMIT different logins with failures in LONG_WINDOW: trying
  a list of logins from one address. Different logins, not failures: a club
  meetup puts everyone behind one Wi-Fi address, and their typos must not
  block the others.
The IP is the real client address that ProxyFix takes from nginx.

The response does not depend on which limit triggered. Failures for
non-existent logins are recorded too, so the response does not reveal whether
the login exists.
"""

import math
from datetime import timedelta

from ..extensions import db
from ..models import LoginFailure, utcnow

PAIR_WINDOW = timedelta(minutes=15)
PAIR_LIMIT = 5
LONG_WINDOW = timedelta(hours=1)
LOGIN_LIMIT = 30
IP_LOGINS_LIMIT = 30


def _wait(times, limit, window, now):
    """Seconds until fewer than limit times are left in the window, None if they already are."""
    times = sorted(time for time in times if time > now - window)
    if len(times) < limit:
        return None
    # Login opens once enough times leave the window to get below the limit.
    unblocked_at = times[-limit] + window
    return max(1, math.ceil((unblocked_at - now).total_seconds()))


def _failure_times(condition, window, now):
    return db.session.scalars(
        db.select(LoginFailure.created_at)
        .where(condition, LoginFailure.created_at > now - window)
    ).all()


def seconds_until_unblocked(login, ip):
    """Seconds to wait until the next attempt, None if no limit is reached."""
    now = utcnow()
    waits = [
        _wait(_failure_times(LoginFailure.login == login, LONG_WINDOW, now),
              LOGIN_LIMIT, LONG_WINDOW, now),
    ]
    if ip:
        pair = (LoginFailure.login == login) & (LoginFailure.ip == ip)
        waits.append(_wait(_failure_times(pair, PAIR_WINDOW, now), PAIR_LIMIT, PAIR_WINDOW, now))
        # The latest failure of each login from this IP: a login stops counting
        # once its latest failure leaves the window.
        latest = db.session.execute(
            db.select(db.func.max(LoginFailure.created_at))
            .where(LoginFailure.ip == ip, LoginFailure.created_at > now - LONG_WINDOW)
            .group_by(LoginFailure.login)
        ).scalars().all()
        waits.append(_wait(latest, IP_LOGINS_LIMIT, LONG_WINDOW, now))
    waits = [wait for wait in waits if wait is not None]
    return max(waits) if waits else None


def record_failure(login, ip):
    now = utcnow()
    db.session.add(LoginFailure(login=login, ip=ip, created_at=now))
    # Also remove records that no longer affect any limit.
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.created_at <= now - LONG_WINDOW))
    db.session.commit()


def clear_pair(login, ip):
    """After a successful login: the user's own typos no longer count.

    Only the pair: failures from other addresses may be someone guessing the password.
    """
    db.session.execute(
        db.delete(LoginFailure).where(LoginFailure.login == login, LoginFailure.ip == ip)
    )
    db.session.commit()


def clear_failures(login):
    """After a password reset: the login is unblocked from all addresses."""
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.login == login))
    db.session.commit()
