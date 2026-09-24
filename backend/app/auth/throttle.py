"""Ограничение попыток входа: не больше MAX_FAILURES неудач на логин за WINDOW.

Считаем только по логину: так проще, а для клубного сервиса этого достаточно.
Неудачи по несуществующим логинам тоже записываются, чтобы ответ
не выдавал, есть ли такой логин.
"""

import math
from datetime import timedelta

from ..extensions import db
from ..models import LoginFailure, utcnow

WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5


def seconds_until_unblocked(login):
    """Сколько секунд ждать до следующей попытки, None — вход не заблокирован."""
    now = utcnow()
    failures = db.session.scalars(
        db.select(LoginFailure.created_at)
        .where(LoginFailure.login == login, LoginFailure.created_at > now - WINDOW)
        .order_by(LoginFailure.created_at)
    ).all()
    if len(failures) < MAX_FAILURES:
        return None
    # Вход откроется, когда из окна выйдет столько неудач, что их станет меньше лимита.
    unblocked_at = failures[-MAX_FAILURES] + WINDOW
    return max(1, math.ceil((unblocked_at - now).total_seconds()))


def record_failure(login):
    now = utcnow()
    db.session.add(LoginFailure(login=login, created_at=now))
    # Заодно убираем записи, которые уже не влияют на блокировку.
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.created_at <= now - WINDOW))
    db.session.commit()


def clear_failures(login):
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.login == login))
    db.session.commit()
