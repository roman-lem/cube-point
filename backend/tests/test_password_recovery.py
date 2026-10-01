"""Password reset by email (app/auth/password_reset.py). Letters go to the test outbox."""

import re
from datetime import timedelta

import pytest

from app.extensions import db
from app.models import LoginFailure, PasswordReset, User

from .helpers import PASSWORD, client_for, create_user, error

NEW_PASSWORD = "brand-new-pass"


@pytest.fixture
def anna(app, client):
    """A user with a confirmed email."""
    create_user(app, "anna")
    set_user(app, "anna", email="anna@example.com")
    return "anna"


def set_user(app, login, **fields):
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == login))
        for name, value in fields.items():
            setattr(user, name, value)
        db.session.commit()


def outbox(app):
    return app.extensions.setdefault("mail_outbox", [])


def last_token(app):
    match = re.search(r"/reset-password#token=(\S+)", outbox(app)[-1]["body"])
    return match and match.group(1)


def request_reset(app, login_or_email, ip="10.0.0.1"):
    return app.test_client().post(
        "/api/auth/password-reset", json={"login_or_email": login_or_email},
        environ_base={"REMOTE_ADDR": ip},
    )


def check(client, token):
    return client.post("/api/auth/password-reset/check", json={"token": token})


def confirm(client, token, password=NEW_PASSWORD):
    return client.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": password})


def login(app, login, password):
    return app.test_client().post("/api/auth/login", json={"login": login, "password": password})


def age_requests(app, delta):
    """Moves all requests back in time (instead of waiting)."""
    with app.app_context():
        for row in db.session.scalars(db.select(PasswordReset)):
            row.created_at -= delta
        db.session.commit()


# Requesting

@pytest.mark.parametrize("login_or_email", ["anna", " ANNA ", "anna@example.com", " Anna@Example.com "])
def test_letter_by_login_or_email(app, anna, login_or_email):
    response = request_reset(app, login_or_email)

    assert response.status_code == 200
    letter = outbox(app)[-1]
    assert letter["to"] == "anna@example.com"
    assert "логин: anna" in letter["body"]
    assert last_token(app)


def test_same_response_for_unknown_account_and_account_without_email(app, anna):
    create_user(app, "boris")  # no email
    responses = [
        request_reset(app, "anna"),
        request_reset(app, "boris"),
        request_reset(app, "nobody"),
        request_reset(app, "nobody@example.com"),
    ]

    assert {r.status_code for r in responses} == {200}
    assert {r.get_data() for r in responses} == {responses[0].get_data()}
    assert [letter["to"] for letter in outbox(app)] == ["anna@example.com"]


def test_deleted_account_gets_no_letter(app, anna):
    client = client_for(app, "anna")
    client.post("/api/auth/delete-account", json={"password": PASSWORD})

    assert request_reset(app, "anna").status_code == 200
    assert request_reset(app, "anna@example.com").status_code == 200
    assert outbox(app) == []


def test_empty_request(app):
    response = request_reset(app, "  ")
    assert error(response)["fields"] == {"login_or_email": "Введите логин или почту"}


# The link

def test_reset_sets_password_and_logs_in(app, anna):
    request_reset(app, "anna")
    token = last_token(app)
    browser = app.test_client()

    assert check(browser, token).get_json() == {"login": "anna"}
    response = confirm(browser, token)

    assert response.status_code == 200
    assert response.get_json()["user"]["login"] == "anna"
    assert browser.get("/api/auth/me").get_json()["user"]["login"] == "anna"
    assert login(app, "anna", PASSWORD).status_code == 401
    assert login(app, "anna", NEW_PASSWORD).status_code == 200


def test_reset_revokes_other_sessions(app, anna):
    old_session = client_for(app, "anna")
    request_reset(app, "anna")

    confirm(app.test_client(), last_token(app))

    assert old_session.get("/api/auth/me").get_json()["user"] is None


def test_reset_removes_forced_change_and_login_block(app, anna):
    set_user(app, "anna", must_change_password=True)
    for _ in range(5):
        login(app, "anna", "wrong-password")
    request_reset(app, "anna")

    response = confirm(app.test_client(), last_token(app))

    assert response.get_json()["user"]["must_change_password"] is False
    with app.app_context():
        assert db.session.scalar(db.select(LoginFailure.id).where(LoginFailure.login == "anna")) is None
    assert login(app, "anna", NEW_PASSWORD).status_code == 200


def test_notification_after_reset(app, anna):
    request_reset(app, "anna")

    confirm(app.test_client(), last_token(app))

    letter = outbox(app)[-1]
    assert letter["to"] == "anna@example.com"
    assert letter["subject"] == "Пароль вашего аккаунта был изменён"
    assert "разработчику" in letter["body"]


def test_link_works_once(app, anna):
    request_reset(app, "anna")
    token = last_token(app)
    confirm(app.test_client(), token)

    for response in (check(app.test_client(), token), confirm(app.test_client(), token, "another-pass")):
        assert response.status_code == 410
        assert error(response)["code"] == "link_used"
    assert login(app, "anna", NEW_PASSWORD).status_code == 200


def test_link_expires_in_an_hour(app, anna):
    request_reset(app, "anna")
    token = last_token(app)
    age_requests(app, timedelta(minutes=59))
    assert check(app.test_client(), token).status_code == 200

    age_requests(app, timedelta(minutes=1))

    response = confirm(app.test_client(), token)
    assert response.status_code == 410
    assert error(response)["code"] == "link_expired"
    assert login(app, "anna", PASSWORD).status_code == 200


def test_new_letter_cancels_old_link(app, anna):
    request_reset(app, "anna")
    old = last_token(app)
    age_requests(app, timedelta(minutes=2))
    request_reset(app, "anna")
    new = last_token(app)

    assert error(confirm(app.test_client(), old))["code"] == "link_cancelled"
    assert confirm(app.test_client(), new).status_code == 200


def test_used_link_cancels_other_links(app, anna):
    """Two letters: the newer one cancels the older, and the reset cancels all open ones."""
    request_reset(app, "anna")
    first = last_token(app)
    confirm(app.test_client(), first)

    assert error(check(app.test_client(), first))["code"] == "link_used"
    with app.app_context():
        open_rows = db.session.scalars(db.select(PasswordReset).where(
            PasswordReset.used_at.is_(None), PasswordReset.cancelled_at.is_(None),
            PasswordReset.token_hash.is_not(None),
        )).all()
    assert open_rows == []


def test_link_stops_working_after_email_change(app, anna):
    request_reset(app, "anna")
    set_user(app, "anna", email="other@example.com")

    assert error(check(app.test_client(), last_token(app)))["code"] == "link_cancelled"


@pytest.mark.parametrize("token", ["", "wrong-token"])
def test_invalid_link(app, anna, token):
    response = confirm(app.test_client(), token)
    assert response.status_code == 404
    assert error(response)["code"] == "link_invalid"


def test_new_password_is_validated(app, anna):
    request_reset(app, "anna")
    token = last_token(app)

    response = confirm(app.test_client(), token, "short")

    assert error(response)["fields"] == {"new_password": "Минимум 8 символов"}
    # The link still works after a validation error.
    assert confirm(app.test_client(), token).status_code == 200


# Rate limits

def test_account_limit_is_silent(app, anna):
    first = request_reset(app, "anna")
    second = request_reset(app, "anna@example.com")

    assert second.status_code == 200
    assert second.get_data() == first.get_data()
    assert len(outbox(app)) == 1

    age_requests(app, timedelta(minutes=1))
    request_reset(app, "anna")
    assert len(outbox(app)) == 2


def test_account_limit_per_hour(app, anna):
    for _ in range(5):
        request_reset(app, "anna")
        age_requests(app, timedelta(minutes=2))
    request_reset(app, "anna")

    assert len(outbox(app)) == 5
    age_requests(app, timedelta(minutes=50))
    request_reset(app, "anna")
    assert len(outbox(app)) == 6


def test_requests_without_letter_do_not_block_owner(app, anna):
    """Someone else's requests over the limit must not keep the owner without letters."""
    request_reset(app, "anna")
    for _ in range(5):
        request_reset(app, "anna", ip="10.0.0.2")
    age_requests(app, timedelta(minutes=1))

    request_reset(app, "anna")
    assert len(outbox(app)) == 2


def test_ip_limit(app, anna):
    for i in range(30):
        assert request_reset(app, f"nobody{i}").status_code == 200

    response = request_reset(app, "anna")

    assert response.status_code == 429
    assert error(response)["code"] == "too_many_requests"
    assert response.headers["Retry-After"]
    assert outbox(app) == []
    # Another address is not affected.
    assert request_reset(app, "anna", ip="10.0.0.2").status_code == 200
    assert len(outbox(app)) == 1


def test_reset_available_to_user_who_must_change_password(app, anna):
    """The endpoints work in a browser where a user with a temporary password is logged in."""
    set_user(app, "anna", must_change_password=True)
    browser = client_for(app, "anna")
    response = browser.post(
        "/api/auth/password-reset", json={"login_or_email": "anna"},
    )
    assert response.status_code == 200
    assert confirm(browser, last_token(app)).status_code == 200
