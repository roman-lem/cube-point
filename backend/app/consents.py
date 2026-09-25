"""Согласия на обработку и на распространение персональных данных.

Тексты согласий — на странице политики (frontend/src/pages/privacy).
При изменении текста меняется версия здесь и в
frontend/src/features/auth/model/consents.ts: клиент присылает версию,
которую показал, и сервер принимает только текущую. Пользователь без согласий
текущей версии не может пользоваться API, пока их не даст (api.require_consents).
"""

from .extensions import db
from .models import ConsentType, UserConsent

CONSENT_VERSIONS = {
    ConsentType.PROCESSING: "2026-09-26",
    ConsentType.PUBLICATION: "2026-09-26",
}


def consent_errors(data):
    """Ошибки полей consent_<тип> для {"consents": {"processing": "<версия>", ...}}."""
    consents = data.get("consents")
    if not isinstance(consents, dict):
        consents = {}
    errors = {}
    for consent_type, version in CONSENT_VERSIONS.items():
        given = consents.get(consent_type.value)
        if not given:
            errors[f"consent_{consent_type.value}"] = "Нужно ваше согласие"
        elif given != version:
            errors[f"consent_{consent_type.value}"] = "Текст согласия обновился, обновите страницу"
    return errors


def consents_required(user):
    """Нет хотя бы одного согласия текущей версии."""
    given = set(db.session.execute(
        db.select(UserConsent.type, UserConsent.version).where(UserConsent.user_id == user.id)
    ).tuples())
    return any((t, v) not in given for t, v in CONSENT_VERSIONS.items())


def record_consents(user):
    """Записывает согласия текущих версий (данные уже проверены consent_errors)."""
    for consent_type, version in CONSENT_VERSIONS.items():
        user.consents.append(UserConsent(type=consent_type, version=version))
