"""Binding an email with confirmation (app/auth/email.py). Letters go to the test outbox."""

import re
import smtplib
from datetime import timedelta

import pytest

from app.extensions import db
from app.models import EmailConfirmation, User

from .helpers import PASSWORD, client_for, create_user, error


@pytest.fixture
def anna(app, client):
    create_user(app, "anna")
    return client_for(app, "anna")


@pytest.fixture
def boris(app, client):
    create_user(app, "boris")
    return client_for(app, "boris")


def outbox(app):
    return app.extensions.setdefault("mail_outbox", [])


def last_token(app):
    match = re.search(r"/confirm-email\?token=(\S+)", outbox(app)[-1]["body"])
    return match and match.group(1)


def request_email(client, address, ip="10.0.0.1"):
    return client.post("/api/auth/email", json={"email": address},
                       environ_base={"REMOTE_ADDR": ip})


def confirm(client, token):
    return client.post("/api/auth/email/confirm", json={"token": token})


def me(client):
    return client.get("/api/auth/me").get_json()["user"]


def user_email(app, login):
    with app.app_context():
        return db.session.scalar(db.select(User.email).where(User.login == login))


def set_email(app, login, address):
    with app.app_context():
        db.session.scalar(db.select(User).where(User.login == login)).email = address
        db.session.commit()


def age_letters(app, delta):
    """Moves all letters back in time (instead of waiting)."""
    with app.app_context():
        for row in db.session.scalars(db.select(EmailConfirmation)):
            row.created_at -= delta
        db.session.commit()


# Requesting and confirming

def test_letter_with_link_and_pending_address(app, anna):
    response = request_email(anna, "  Anna@Example.com ")

    assert response.status_code == 200
    assert response.get_json() == {
        "email": None, "pending_email": {"address": "anna@example.com", "expired": False},
    }
    letter = outbox(app)[-1]
    assert letter["to"] == "anna@example.com"
    assert last_token(app)
    # Not bound until confirmed.
    assert user_email(app, "anna") is None
    assert me(anna)["pending_email"]["address"] == "anna@example.com"


def test_confirm_binds_email(app, anna):
    request_email(anna, "anna@example.com")

    # The link is opened without logging in, e.g. on another device.
    response = confirm(app.test_client(), last_token(app))

    assert response.status_code == 200
    assert response.get_json() == {"email": "anna@example.com"}
    assert me(anna)["email"] == "anna@example.com"
    assert me(anna)["pending_email"] is None


def test_link_works_once(app, anna):
    request_email(anna, "anna@example.com")
    token = last_token(app)
    confirm(anna, token)

    response = confirm(anna, token)

    assert response.status_code == 410
    assert error(response)["code"] == "link_used"


def test_expired_link(app, anna):
    request_email(anna, "anna@example.com")
    age_letters(app, timedelta(hours=24, seconds=1))

    response = confirm(anna, last_token(app))

    assert response.status_code == 410
    assert error(response)["code"] == "link_expired"
    assert user_email(app, "anna") is None
    assert me(anna)["pending_email"] == {"address": "anna@example.com", "expired": True}


def test_unknown_link(app, anna):
    for token in ["", "nonsense"]:
        response = confirm(anna, token)
        assert response.status_code == 404
        assert error(response)["code"] == "link_invalid"


def test_new_letter_cancels_previous_link(app, anna):
    request_email(anna, "first@example.com")
    first = last_token(app)
    age_letters(app, timedelta(minutes=2))
    request_email(anna, "second@example.com")

    response = confirm(anna, first)

    assert response.status_code == 410
    assert error(response)["code"] == "link_cancelled"
    assert confirm(anna, last_token(app)).status_code == 200
    assert user_email(app, "anna") == "second@example.com"


def test_cancel_pending(app, anna):
    request_email(anna, "anna@example.com")
    token = last_token(app)

    response = anna.delete("/api/auth/email/pending")

    assert response.get_json()["pending_email"] is None
    assert confirm(anna, token).status_code == 410


def test_invalid_address(app, anna):
    for address in ["", "anna", "anna@", "anna@example", "an na@example.com",
                    "anna@example.com\nBcc: x@example.com", "анна@пример.рф"]:
        response = request_email(anna, address)
        assert response.status_code == 422, address
        assert "email" in error(response)["fields"]
    assert outbox(app) == []


def test_requires_login(client):
    assert request_email(client, "anna@example.com").status_code == 401
    assert client.post("/api/auth/email/remove", json={"password": PASSWORD}).status_code == 401


# Changing and removing

def test_change_keeps_old_until_confirmed(app, anna):
    set_email(app, "anna", "old@example.com")

    request_email(anna, "new@example.com")

    assert me(anna)["email"] == "old@example.com"
    assert me(anna)["pending_email"]["address"] == "new@example.com"

    confirm(anna, last_token(app))

    assert user_email(app, "anna") == "new@example.com"
    # The old address is told about the change, without the new one.
    notice = outbox(app)[-1]
    assert notice["to"] == "old@example.com"
    assert "изменена" in notice["body"]
    assert "new@example.com" not in notice["body"]


def test_own_address_again(app, anna):
    set_email(app, "anna", "anna@example.com")

    response = request_email(anna, "ANNA@example.com")

    assert response.status_code == 422
    assert outbox(app) == []


def test_remove_needs_password(app, anna):
    set_email(app, "anna", "anna@example.com")

    for password, message in [("", "Введите пароль"), ("wrong-pass", "Неверный пароль")]:
        response = anna.post("/api/auth/email/remove", json={"password": password})
        assert response.status_code == 422
        assert error(response)["fields"]["password"] == message
    assert user_email(app, "anna") == "anna@example.com"

    response = anna.post("/api/auth/email/remove", json={"password": PASSWORD})

    assert response.status_code == 200
    assert response.get_json()["email"] is None
    assert user_email(app, "anna") is None


# One address, one account

def test_taken_address_gets_the_same_response(app, anna, boris):
    set_email(app, "boris", "boris@example.com")

    taken = request_email(anna, "Boris@example.com")
    free = request_email(boris, "free@example.com", ip="10.0.0.2")

    # The response does not tell a taken address from a free one.
    assert taken.status_code == free.status_code == 200
    assert taken.get_json()["pending_email"] == {"address": "boris@example.com", "expired": False}
    # The owner gets a letter without a link.
    letter = outbox(app)[0]
    assert letter["to"] == "boris@example.com"
    assert "уже привязан" in letter["body"]
    assert "token=" not in letter["body"]
    assert user_email(app, "boris") == "boris@example.com"


def test_address_taken_before_confirmation(app, anna, boris):
    request_email(anna, "shared@example.com")
    anna_token = last_token(app)
    request_email(boris, "shared@example.com", ip="10.0.0.2")
    assert confirm(boris, last_token(app)).status_code == 200

    response = confirm(anna, anna_token)

    assert response.status_code == 409
    assert error(response)["code"] == "email_taken"
    assert user_email(app, "anna") is None
    assert me(anna)["pending_email"] is None


# Rate limits

def test_one_letter_per_minute(app, anna):
    request_email(anna, "anna@example.com")

    response = request_email(anna, "anna@example.com")

    assert response.status_code == 429
    assert error(response)["code"] == "too_many_letters"
    assert 0 < error(response)["retry_after"] <= 60
    assert len(outbox(app)) == 1


def test_letters_per_hour_per_user(app, anna):
    for _ in range(5):
        assert request_email(anna, "anna@example.com").status_code == 200
        age_letters(app, timedelta(minutes=2))

    response = request_email(anna, "anna@example.com")

    assert response.status_code == 429
    assert len(outbox(app)) == 5
    # The oldest letter leaves the hour window.
    age_letters(app, timedelta(minutes=51))
    assert request_email(anna, "anna@example.com").status_code == 200


def test_letters_per_ip(app, client):
    for number in range(30):
        create_user(app, f"user{number}")
        response = request_email(client_for(app, f"user{number}"), f"user{number}@example.com")
        assert response.status_code == 200

    create_user(app, "late")
    late = client_for(app, "late")
    assert request_email(late, "late@example.com").status_code == 429
    # Another address is not affected.
    assert request_email(late, "late@example.com", ip="10.0.0.9").status_code == 200


def test_taken_address_counts_for_limits(app, anna, boris):
    set_email(app, "boris", "boris@example.com")
    request_email(anna, "boris@example.com")

    assert request_email(anna, "anna@example.com").status_code == 429


# Sending

def test_send_error(app, anna, monkeypatch):
    app.config.update(MAIL_HOST="mail.example.com", MAIL_USERNAME="noreply@example.com")

    def broken(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(smtplib, "SMTP_SSL", broken)

    response = request_email(anna, "anna@example.com")

    assert response.status_code == 503
    assert error(response)["code"] == "mail_failed"
    assert me(anna)["pending_email"] is None
    # The failed letter counts for the limits.
    assert request_email(anna, "anna@example.com").status_code == 429


def test_smtp_settings(app, anna, monkeypatch):
    app.config.update(
        MAIL_HOST="mail.example.com", MAIL_PORT=465, MAIL_USERNAME="noreply@example.com",
        MAIL_PASSWORD="mail-pass", MAIL_FROM="Сайт <noreply@example.com>",
    )
    sent = []

    class FakeSmtp:
        def __init__(self, host, port, timeout, context):
            sent.append({"host": host, "port": port, "timeout": timeout})

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, user, password):
            sent.append({"login": (user, password)})

        def send_message(self, message):
            sent.append({"to": message["To"], "from": message["From"]})

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSmtp)

    assert request_email(anna, "anna@example.com").status_code == 200
    assert sent[0] == {"host": "mail.example.com", "port": 465, "timeout": 5}
    assert sent[1] == {"login": ("noreply@example.com", "mail-pass")}
    assert sent[2]["to"] == "anna@example.com"
    assert "noreply@example.com" in sent[2]["from"]


# Account deletion

def test_deleting_account_removes_letters(app, anna):
    request_email(anna, "anna@example.com")
    token = last_token(app)

    anna.post("/api/auth/delete-account", json={"password": PASSWORD})

    with app.app_context():
        assert db.session.scalars(db.select(EmailConfirmation)).all() == []
    assert confirm(app.test_client(), token).status_code == 404

