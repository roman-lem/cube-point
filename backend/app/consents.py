"""Consents to processing and to publication of personal data.

The consent texts are on the privacy policy page (frontend/src/pages/privacy).
When a text changes, the version changes both here and in
frontend/src/features/auth/model/consents.ts: the client sends the version
it displayed, and the server accepts only the current one. A user without the
current consents cannot use the API until they give them (api.require_consents).
"""

from .extensions import db
from .models import ConsentType, UserConsent

CONSENT_VERSIONS = {
    ConsentType.PROCESSING: "2026-09-26",
    ConsentType.PUBLICATION: "2026-09-26",
}


def consent_errors(data):
    """Errors of consent_<type> fields for {"consents": {"processing": "<version>", ...}}."""
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
    """At least one current-version consent is missing."""
    given = set(db.session.execute(
        db.select(UserConsent.type, UserConsent.version).where(UserConsent.user_id == user.id)
    ).tuples())
    return any((t, v) not in given for t, v in CONSENT_VERSIONS.items())


def record_consents(user):
    """Records the current-version consents (data already checked by consent_errors)."""
    for consent_type, version in CONSENT_VERSIONS.items():
        user.consents.append(UserConsent(type=consent_type, version=version))
