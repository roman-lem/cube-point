"""Rules for a password the user sets (auth.validation.new_password_error):
not the login (ignoring case) and not the current password, in every place."""

import re

import pytest

from app.consents import CONSENT_VERSIONS
from app.extensions import db
from app.models import User

from .helpers import PASSWORD, client_for, create_user, error, registration_form

SAME_AS_LOGIN = "Пароль не должен совпадать с логином"
SAME_AS_CURRENT = "Новый пароль совпадает с текущим"
LOGIN = "ivan_petrov"


@pytest.fixture
def ivan(app, client):
    create_user(app, LOGIN)
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == LOGIN))
        user.email = "ivan@example.com"
        db.session.commit()


def register(app, password):
    client = app.test_client()
    return client.post("/api/auth/register", json={
        **registration_form(client),
        "display_name": "Иван Петров", "login": LOGIN, "password": password,
        "consents": {t.value: v for t, v in CONSENT_VERSIONS.items()},
    })


def change(app, password):
    return client_for(app, LOGIN).post("/api/auth/password", json={
        "current_password": PASSWORD, "new_password": password,
    })


def forced_change(app, password):
    with app.app_context():
        db.session.scalar(db.select(User).where(User.login == LOGIN)).must_change_password = True
        db.session.commit()
    return client_for(app, LOGIN).post("/api/auth/password", json={"new_password": password})


def reset_by_email(app, password):
    app.test_client().post("/api/auth/password-reset", json={"login_or_email": LOGIN})
    token = re.search(r"token=(\S+)", app.extensions["mail_outbox"][-1]["body"]).group(1)
    return app.test_client().post(
        "/api/auth/password-reset/confirm", json={"token": token, "new_password": password},
    )


@pytest.mark.parametrize("password", [LOGIN, LOGIN.upper(), "Ivan_Petrov"])
def test_register_rejects_login_as_password(app, client, password):
    response = register(app, password)

    assert response.status_code == 422
    assert error(response)["fields"] == {"password": SAME_AS_LOGIN}


SET_PASSWORD = {"change": change, "forced_change": forced_change, "reset_by_email": reset_by_email}


@pytest.mark.parametrize("place", SET_PASSWORD)
@pytest.mark.parametrize("password", [LOGIN, LOGIN.upper()])
def test_new_password_is_not_login(app, ivan, place, password):
    response = SET_PASSWORD[place](app, password)

    assert response.status_code == 422
    assert error(response)["fields"] == {"new_password": SAME_AS_LOGIN}


@pytest.mark.parametrize("place", SET_PASSWORD)
def test_new_password_is_not_current(app, ivan, place):
    """For a forced change the current password is the temporary one: it cannot be kept."""
    response = SET_PASSWORD[place](app, PASSWORD)

    assert response.status_code == 422
    assert error(response)["fields"] == {"new_password": SAME_AS_CURRENT}


@pytest.mark.parametrize("place", SET_PASSWORD)
def test_other_password_is_accepted(app, ivan, place):
    assert SET_PASSWORD[place](app, "brand-new-pass").status_code == 200


def test_login_inside_password_is_allowed(app, client):
    """Only an exact match is rejected."""
    response = register(app, LOGIN + "-2026")
    assert response.status_code == 201
