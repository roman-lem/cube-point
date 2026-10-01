from datetime import timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.auth import registration, throttle
from app.consents import CONSENT_VERSIONS
from app.extensions import db
from app.models import LoginFailure, Registration, User, utcnow

from .conftest import TEST_CONFIG
from .helpers import registration_form

PASSWORD = "secret-pass"
CONSENTS = {t.value: version for t, version in CONSENT_VERSIONS.items()}


def register(client, login="ivan_petrov", display_name="Иван Петров", password=PASSWORD,
             consents=CONSENTS, ip="127.0.0.1", **form):
    """form overrides the fields of the bot protection (registration_form)."""
    return client.post("/api/auth/register", json={
        **registration_form(client),
        "display_name": display_name, "login": login, "password": password,
        "consents": consents, **form,
    }, environ_base={"REMOTE_ADDR": ip})


def login(client, login="ivan_petrov", password=PASSWORD, remember=False):
    return client.post("/api/auth/login", json={
        "login": login, "password": password, "remember": remember,
    })


def me(client):
    return client.get("/api/auth/me").get_json()["user"]


def update_user(app, login, **fields):
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == login))
        for name, value in fields.items():
            setattr(user, name, value)
        db.session.commit()


def bump_session_version(app, login):
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == login))
        user.session_version += 1
        db.session.commit()


def error(response):
    return response.get_json()["error"]


# Registration

def test_register_creates_user_and_logs_in(client):
    response = register(client, login="Ivan_Petrov", display_name="  Иван   Петров ")

    assert response.status_code == 201
    user = response.get_json()["user"]
    assert user["login"] == "ivan_petrov"
    assert user["display_name"] == "Иван Петров"
    assert user["must_change_password"] is False
    assert me(client)["id"] == user["id"]


def test_register_duplicate_login_in_other_case(client, app):
    register(client, login="ivan_petrov")

    response = register(app.test_client(), login="IVAN_Petrov")

    assert response.status_code == 422
    assert error(response)["code"] == "validation_error"
    assert error(response)["fields"] == {"login": "Логин уже занят"}


@pytest.mark.parametrize("field, value", [
    ("login", ""),
    ("login", "ab"),
    ("login", "a" * 33),
    ("login", "иван"),
    ("login", "_ivan"),
    ("login", "ivan petrov"),
    ("display_name", ""),
    ("display_name", "И"),
    ("display_name", "x" * 101),
    ("display_name", "2000"),
    ("display_name", "__"),
    ("display_name", "Иван!"),
    ("display_name", "Удалённый участник"),
    ("display_name", "удаленный УЧАСТНИК"),
    ("password", ""),
    ("password", "short"),
    ("password", "x" * 129),
])
def test_register_invalid_field(client, field, value):
    data = {"login": "ivan_petrov", "display_name": "Иван Петров", "password": PASSWORD}
    data[field] = value

    response = register(client, **data)

    assert response.status_code == 422
    assert list(error(response)["fields"]) == [field]


@pytest.mark.parametrize("display_name", [
    "Анна-Мария Д'Артаньян", "Jean Dupont", "Ли Мин Хо", "Ли", "alex_cube", "Cuber 2000",
    "st.petrov",
])
def test_register_accepts_names_and_nicknames(client, display_name):
    assert register(client, display_name=display_name).status_code == 201


def test_register_reports_all_invalid_fields(client):
    response = client.post("/api/auth/register", json=registration_form(client))

    assert set(error(response)["fields"]) == {
        "display_name", "login", "password",
        "consent_processing", "consent_publication", "consent_age",
    }


# Consents

def consent_rows(app, login="ivan_petrov"):
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == login))
        return [(c.type.value, c.version, c.accepted_at) for c in user.consents]


def test_register_saves_consents_with_version_and_date(client, app):
    register(client)

    rows = consent_rows(app)
    assert {t for t, _, _ in rows} == {"processing", "publication", "age"}
    assert {(t, v) for t, v, _ in rows} == set(CONSENTS.items())
    assert all(accepted_at is not None for _, _, accepted_at in rows)
    assert me(client)["consents_required"] is False


@pytest.mark.parametrize("missing,message", [
    ("processing", "Нужно ваше согласие"),
    ("publication", "Нужно ваше согласие"),
    ("age", "Нужно подтверждение"),
])
def test_register_requires_each_consent(client, app, missing, message):
    consents = {**CONSENTS, missing: None}

    response = register(client, consents=consents)

    assert response.status_code == 422
    assert error(response)["fields"] == {f"consent_{missing}": message}
    with app.app_context():
        assert db.session.scalar(db.select(User).where(User.login == "ivan_petrov")) is None


@pytest.mark.parametrize("consent", ["publication", "age"])
def test_register_rejects_outdated_consent_version(client, consent):
    response = register(client, consents={**CONSENTS, consent: "2000-01-01"})

    assert response.status_code == 422
    assert error(response)["fields"] == {
        f"consent_{consent}": "Текст согласия обновился, обновите страницу",
    }


def create_account_without_consents(app, login="newbie"):
    """An account created by an organizer: no consents."""
    with app.app_context():
        db.session.add(User(
            login=login, display_name="Новичок", password_hash=generate_password_hash(PASSWORD),
        ))
        db.session.commit()


def test_account_without_consents_must_accept_them(client, app):
    create_account_without_consents(app)
    login(client, login="newbie")

    assert me(client)["consents_required"] is True
    blocked = client.get("/api/clubs")
    assert blocked.status_code == 403
    assert error(blocked)["code"] == "consents_required"

    missing = client.post("/api/auth/consents", json={"consents": {"processing": CONSENTS["processing"]}})
    assert missing.status_code == 422
    assert set(error(missing)["fields"]) == {"consent_publication", "consent_age"}

    response = client.post("/api/auth/consents", json={"consents": CONSENTS})
    assert response.status_code == 200
    assert response.get_json()["user"]["consents_required"] is False
    assert {(t, v) for t, v, _ in consent_rows(app, "newbie")} == set(CONSENTS.items())
    assert client.get("/api/clubs").status_code == 200


def test_new_consent_version_is_asked_again(client, app, monkeypatch):
    register(client)
    new_versions = {**CONSENT_VERSIONS}
    new_versions[next(iter(new_versions))] = "2099-01-01"
    monkeypatch.setattr("app.consents.CONSENT_VERSIONS", new_versions)

    assert me(client)["consents_required"] is True
    assert client.get("/api/clubs").status_code == 403

    new_consents = {t.value: v for t, v in new_versions.items()}
    assert client.post("/api/auth/consents", json={"consents": new_consents}).status_code == 200
    # Earlier entries stay: the consent log is append-only.
    assert len(consent_rows(app)) == 6
    assert client.get("/api/clubs").status_code == 200


def test_user_without_age_confirmation_is_asked(client, app):
    """Users registered before the age confirmation give it on the consent page."""
    register(client)
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == "ivan_petrov"))
        for consent in [c for c in user.consents if c.type.value == "age"]:
            db.session.delete(consent)
        db.session.commit()

    assert me(client)["consents_required"] is True
    assert error(client.get("/api/clubs"))["code"] == "consents_required"
    assert client.post("/api/auth/consents", json={"consents": CONSENTS}).status_code == 200
    assert client.get("/api/clubs").status_code == 200


# Closed registration

def test_registration_open_by_default(client):
    assert client.get("/api/auth/registration").get_json()["open"] is True


def test_closed_registration_rejects_register_but_allows_login(client, app):
    register(client)
    app.config["REGISTRATION_OPEN"] = False
    browser = app.test_client()

    assert browser.get("/api/auth/registration").get_json()["open"] is False
    response = register(browser, login="another_user")
    assert response.status_code == 403
    assert error(response)["code"] == "registration_closed"
    assert login(browser).status_code == 200


def test_register_with_non_json_body(client):
    response = client.post("/api/auth/register", data="not json")

    # Without the form token it is rejected before validation.
    assert response.status_code == 400
    assert error(response)["code"] == "registration_rejected"


# Login and logout

def test_login_and_logout(client, app):
    register(client)
    guest = app.test_client()
    assert me(guest) is None

    response = login(guest, login="Ivan_Petrov")
    assert response.status_code == 200
    assert response.get_json()["user"]["login"] == "ivan_petrov"
    assert me(guest)["login"] == "ivan_petrov"

    assert guest.post("/api/auth/logout").status_code == 204
    assert me(guest) is None


def test_login_wrong_password(client, app):
    register(client)

    response = login(app.test_client(), password="wrong-password")

    assert response.status_code == 401
    assert error(response)["code"] == "invalid_credentials"
    assert "fields" not in error(response)


def test_login_unknown_user_looks_like_wrong_password(client):
    response = login(client, login="nobody")

    assert response.status_code == 401
    assert error(response)["code"] == "invalid_credentials"


def test_login_empty_fields(client):
    response = client.post("/api/auth/login", json={})

    assert response.status_code == 422
    assert set(error(response)["fields"]) == {"login", "password"}


def test_protected_endpoint_without_session(client):
    response = client.post("/api/auth/password", json={"new_password": "new-secret"})

    assert response.status_code == 401
    assert error(response)["code"] == "unauthorized"


def test_unknown_api_path_returns_json_error(client):
    response = client.get("/api/nope")

    assert response.status_code == 404
    assert error(response)["code"] == "not_found"


# Session revocation

def test_session_is_revoked_when_session_version_changes(client, app):
    register(client)
    assert me(client) is not None

    bump_session_version(app, "ivan_petrov")

    assert me(client) is None


def test_remember_cookie_restores_session(client, app):
    register(client)
    browser = app.test_client()
    login(browser, remember=True)

    # The browser was closed: the session cookie is gone, the remember cookie stays.
    browser.delete_cookie("session")

    assert me(browser)["login"] == "ivan_petrov"


def test_remember_cookie_is_revoked_when_session_version_changes(client, app):
    register(client)
    browser = app.test_client()
    login(browser, remember=True)
    browser.delete_cookie("session")

    bump_session_version(app, "ivan_petrov")

    assert me(browser) is None


def test_session_without_remember_ends_with_browser(client, app):
    register(client)
    browser = app.test_client()
    login(browser, remember=False)

    browser.delete_cookie("session")

    assert me(browser) is None


def test_session_cookie_flags(client):
    response = register(client)

    cookies = response.headers.getlist("Set-Cookie")
    assert any(c.startswith("session=") and "HttpOnly" in c and "SameSite=Lax" in c
               for c in cookies)
    assert any(c.startswith("remember_token=") and "HttpOnly" in c and "SameSite=Lax" in c
               for c in cookies)


# Password change

def test_change_password_revokes_other_sessions(client, app):
    register(client)
    other_device = app.test_client()
    login(other_device, remember=True)

    response = client.post("/api/auth/password", json={
        "current_password": PASSWORD, "new_password": "brand-new-pass",
    })

    assert response.status_code == 200
    assert me(client)["login"] == "ivan_petrov"
    assert me(other_device) is None
    assert login(app.test_client(), password="brand-new-pass").status_code == 200


def test_change_password_requires_correct_current_password(client):
    register(client)

    response = client.post("/api/auth/password", json={
        "current_password": "wrong-password", "new_password": "brand-new-pass",
    })

    assert response.status_code == 422
    assert error(response)["fields"] == {"current_password": "Неверный пароль"}


def test_change_password_rejects_same_password(client):
    register(client)

    response = client.post("/api/auth/password", json={
        "current_password": PASSWORD, "new_password": PASSWORD,
    })

    assert error(response)["fields"] == {"new_password": "Новый пароль совпадает с текущим"}


def test_must_change_password_allows_only_password_change(client, app):
    register(client)
    update_user(
        app, "ivan_petrov",
        password_hash=generate_password_hash("temp-pass-123"),
        must_change_password=True,
    )
    browser = app.test_client()
    assert login(browser, password="temp-pass-123").get_json()["user"]["must_change_password"]

    assert browser.get("/api/health").status_code == 200
    assert me(browser)["must_change_password"] is True
    blocked = browser.post("/api/auth/register", json={})
    assert blocked.status_code == 403
    assert error(blocked)["code"] == "password_change_required"

    # The current (temporary) password is not needed for a forced change.
    response = browser.post("/api/auth/password", json={"new_password": "brand-new-pass"})

    assert response.status_code == 200
    assert response.get_json()["user"]["must_change_password"] is False
    assert browser.post("/api/auth/register", json=registration_form(browser)).status_code == 422


# Login throttling

def age_failures(app, delta):
    """Moves all failures back in time (instead of waiting)."""
    with app.app_context():
        for failure in db.session.scalars(db.select(LoginFailure)):
            failure.created_at -= delta
        db.session.commit()


# nginx appends the address it sees as the last X-Forwarded-For entry.
def login_from(client, ip, spoofed=None, login="ivan_petrov", password=PASSWORD):
    forwarded = f"{spoofed}, {ip}" if spoofed else ip
    return client.post("/api/auth/login", json={"login": login, "password": password},
                       headers={"X-Forwarded-For": forwarded})


def fail(client, ip, times, login="ivan_petrov"):
    for _ in range(times):
        assert login_from(client, ip, login=login, password="wrong-password").status_code == 401


def fail_from_ip(client, ip, logins, spoofed=None):
    # A new login each time: only the limit on different logins per IP can trigger.
    for i in range(logins):
        response = login_from(client, ip, spoofed, login=f"guess_{i}", password="wrong-password")
        assert response.status_code == 401


def assert_blocked(response, window):
    # The same response whichever limit triggered.
    assert response.status_code == 429
    assert error(response)["code"] == "too_many_attempts"
    assert error(response)["message"].startswith("Слишком много неудачных попыток")
    retry_after = error(response)["retry_after"]
    assert 0 < retry_after <= window.total_seconds()
    assert response.headers["Retry-After"] == str(retry_after)


def test_failures_block_the_pair_even_with_correct_password(client, app):
    register(client)
    register(app.test_client(), login="anna")
    fail(client, "203.0.113.7", throttle.PAIR_LIMIT)

    assert_blocked(login_from(client, "203.0.113.7", login="IVAN_PETROV"), throttle.PAIR_WINDOW)
    # Only this login and only from this address.
    assert login_from(client, "198.51.100.20").status_code == 200
    assert login_from(client, "203.0.113.7", login="anna").status_code == 200


def test_pair_block_expires_after_window(client, app):
    register(client)
    fail(client, "203.0.113.7", throttle.PAIR_LIMIT)

    age_failures(app, throttle.PAIR_WINDOW)

    assert login_from(client, "203.0.113.7").status_code == 200


def test_successful_login_resets_own_failures(client, app):
    register(client)
    fail(client, "203.0.113.7", throttle.PAIR_LIMIT - 1)

    assert login_from(client, "203.0.113.7").status_code == 200
    fail(client, "203.0.113.7", throttle.PAIR_LIMIT - 1)

    assert login_from(client, "203.0.113.7").status_code == 200


def test_meetup_mistakes_do_not_block_others(client, app):
    # Everybody at a meetup is behind one Wi-Fi address.
    register(client)
    for number in range(throttle.IP_LOGINS_LIMIT - 2):
        fail(client, "203.0.113.7", 2, login=f"participant_{number}")
    # One participant is blocked, only for their own login.
    fail(client, "203.0.113.7", throttle.PAIR_LIMIT, login="forgetful")
    assert login_from(client, "203.0.113.7", login="forgetful").status_code == 429

    assert login_from(client, "203.0.113.7").status_code == 200


def test_one_login_guessed_from_many_ips_is_blocked(client, app):
    register(client)
    for number in range(throttle.LOGIN_LIMIT // 3):
        fail(client, f"203.0.113.{number}", 3)

    assert_blocked(login_from(client, "198.51.100.20"), throttle.LONG_WINDOW)
    age_failures(app, throttle.LONG_WINDOW)
    assert login_from(client, "198.51.100.20").status_code == 200


def test_owner_login_does_not_reset_guessing_from_other_ips(client, app):
    register(client)
    for number in range(throttle.LOGIN_LIMIT - 1):
        fail(client, f"203.0.113.{number}", 1)

    assert login_from(client, "198.51.100.20").status_code == 200
    fail(client, "203.0.113.200", 1)

    assert login_from(client, "198.51.100.20").status_code == 429


def test_many_logins_from_one_ip_block_it(client, app):
    register(client)
    fail_from_ip(client, "203.0.113.7", throttle.IP_LOGINS_LIMIT)

    assert_blocked(login_from(client, "203.0.113.7"), throttle.LONG_WINDOW)
    # The same login from another address works: the block is per IP.
    assert login_from(client, "198.51.100.20").status_code == 200
    age_failures(app, throttle.LONG_WINDOW)
    assert login_from(client, "203.0.113.7").status_code == 200


def test_ip_limit_uses_real_ip_behind_proxy(client, app):
    register(client)
    fail_from_ip(client, "203.0.113.7", throttle.IP_LOGINS_LIMIT - 1, spoofed="10.0.0.1")

    # A client that sends its own X-Forwarded-For does not get a fresh address:
    # the entry nginx appended (the real IP) is the one counted.
    response = login_from(client, "203.0.113.7", spoofed="10.0.0.2",
                          login="guess_last", password="wrong-password")
    assert response.status_code == 401

    assert login_from(client, "203.0.113.7", spoofed="10.0.0.3").status_code == 429
    with app.app_context():
        ips = set(db.session.scalars(db.select(LoginFailure.ip)))
    assert ips == {"203.0.113.7"}


def test_old_failures_are_removed(client, app):
    register(client)
    fail(client, "203.0.113.7", 1)
    age_failures(app, throttle.LONG_WINDOW)

    fail(client, "203.0.113.8", 1)

    with app.app_context():
        assert db.session.scalars(db.select(LoginFailure.ip)).all() == ["203.0.113.8"]


# Registration protection

def registration_rows(app, ip, count, age=timedelta(minutes=1)):
    with app.app_context():
        for _ in range(count):
            db.session.add(Registration(ip=ip, created_at=utcnow() - age))
        db.session.commit()


def user_count(app):
    with app.app_context():
        return db.session.scalar(db.select(db.func.count(User.id)))


def assert_rejected(app, response):
    # Without saying why.
    assert response.status_code == 400
    assert error(response)["code"] == "registration_rejected"
    assert user_count(app) == 0


def test_registration_gives_form_token(client):
    token = client.get("/api/auth/registration").get_json()["form_token"]

    assert isinstance(token, str) and token


def test_register_after_min_fill_time(client, app, monkeypatch):
    token = client.get("/api/auth/registration").get_json()["form_token"]
    later = utcnow() + registration.MIN_FILL_TIME
    monkeypatch.setattr("app.auth.routes.utcnow", lambda: later)

    assert register(client, form_token=token).status_code == 201


def test_register_too_fast_is_rejected(client, app):
    token = client.get("/api/auth/registration").get_json()["form_token"]

    assert_rejected(app, register(client, form_token=token))


@pytest.mark.parametrize("token", [None, "", "forged.token", 12345])
def test_register_without_valid_form_token_is_rejected(client, app, token):
    assert_rejected(app, register(client, form_token=token))


def test_register_with_stale_form_token_is_rejected(client, app):
    with app.app_context():
        token = registration.form_token(
            utcnow() - registration.MAX_FORM_AGE - timedelta(minutes=1),
        )

    assert_rejected(app, register(client, form_token=token))


def test_register_with_filled_trap_is_rejected(client, app):
    assert_rejected(app, register(client, **{registration.TRAP_FIELD: "https://spam.example"}))


def test_registration_is_journaled_without_ip_in_users(client, app):
    register(client, ip="203.0.113.7")

    with app.app_context():
        assert db.session.scalars(db.select(Registration.ip)).all() == ["203.0.113.7"]
    assert "ip" not in User.__table__.columns


def test_registrations_per_ip_per_hour(client, app):
    registration_rows(app, "203.0.113.7", registration.IP_HOURLY_LIMIT)

    response = register(client, ip="203.0.113.7")

    assert response.status_code == 429
    assert error(response)["code"] == "too_many_registrations"
    assert user_count(app) == 0
    # Another address is not affected.
    assert register(client, ip="198.51.100.20").status_code == 201


def test_registrations_per_ip_per_day(client, app):
    # Outside the hour, inside the day.
    registration_rows(app, "203.0.113.7", registration.IP_DAILY_LIMIT, age=timedelta(hours=2))

    response = register(client, ip="203.0.113.7")

    assert response.status_code == 429
    assert error(response)["code"] == "too_many_registrations"
    assert register(client, ip="198.51.100.20").status_code == 201


def test_registrations_older_than_a_day_are_removed(client, app):
    registration_rows(
        app, "203.0.113.7", registration.IP_DAILY_LIMIT, age=timedelta(days=1, minutes=1),
    )

    assert register(client, ip="203.0.113.7").status_code == 201
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Registration.id))) == 1


def test_registration_fuse(client, app, caplog):
    with app.app_context():
        for number in range(registration.TOTAL_HOURLY_LIMIT):
            db.session.add(Registration(ip=f"10.0.{number // 250}.{number % 250}"))
        db.session.commit()

    response = register(client, ip="198.51.100.20")

    assert response.status_code == 503
    assert error(response)["code"] == "registration_unavailable"
    assert error(response)["message"] == "Регистрация временно недоступна"
    assert user_count(app) == 0
    assert "Registration fuse" in caplog.text


# Logout everywhere

def test_logout_everywhere_ends_all_sessions(client, app):
    register(client)
    phone = app.test_client()
    login(phone, remember=True)
    # Only the remember cookie is left on the phone: it must stop working too.
    phone.delete_cookie("session")

    assert client.post("/api/auth/logout-everywhere").status_code == 204

    assert me(client) is None
    assert me(phone) is None
    # The password still works.
    assert login(client).status_code == 200


def test_logout_everywhere_needs_login(client):
    assert client.post("/api/auth/logout-everywhere").status_code == 401


def test_forwarded_proto_is_seen_by_flask(app):
    @app.get("/api/test-scheme")
    def scheme():
        from flask import request
        return {"scheme": request.scheme}

    response = app.test_client().get("/api/test-scheme", headers={"X-Forwarded-Proto": "https"})

    assert response.get_json() == {"scheme": "https"}


# CSRF

@pytest.fixture
def csrf_client():
    app = create_app({**TEST_CONFIG, "WTF_CSRF_ENABLED": True})
    with app.app_context():
        db.create_all()
    return app.test_client()


def test_request_without_csrf_token_is_rejected(csrf_client):
    response = register(csrf_client)

    assert response.status_code == 400
    assert error(response)["code"] == "csrf_failed"


def test_request_with_csrf_token_is_accepted(csrf_client):
    token = csrf_client.get("/api/auth/csrf").get_json()["csrf_token"]

    response = csrf_client.post(
        "/api/auth/register",
        json={
            **registration_form(csrf_client),
            "display_name": "Иван Петров", "login": "ivan_petrov", "password": PASSWORD,
            "consents": CONSENTS,
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    # After login the same token keeps working.
    logout = csrf_client.post("/api/auth/logout", headers={"X-CSRFToken": token})
    assert logout.status_code == 204
