"""The administrator's user list and card, password reset by the administrator."""

import pytest

from app.extensions import db
from app.models import ClubMember, User, utcnow

from .helpers import MEMBER, ORGANIZER, PASSWORD, client_for, create_club, create_user, error
from .test_admin import delete_account


@pytest.fixture
def club_id(app, client):
    club_id = create_club(app)
    create_user(app, "org", ORGANIZER, club_id)
    create_user(app, "member", MEMBER, club_id)
    return club_id


@pytest.fixture
def admin(app, club_id):
    user_id = create_user(app, "admin")
    with app.app_context():
        user = db.session.get(User, user_id)
        user.is_admin = True
        user.display_name = "Админ"
        db.session.commit()
    return client_for(app, "admin")


def set_user(app, login, **fields):
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == login))
        for name, value in fields.items():
            setattr(user, name, value)
        db.session.commit()
        return user.id


def logins(admin, query="", filter_name="all", offset=0):
    response = admin.get(f"/api/admin/users?q={query}&filter={filter_name}&offset={offset}")
    assert response.status_code == 200
    return [u["login"] for u in response.get_json()["users"]]


@pytest.mark.parametrize("login", [None, "member", "org"])
def test_only_admin_has_access(app, club_id, login):
    client = client_for(app, login) if login else app.test_client()
    member = set_user(app, "member")
    expected = 401 if login is None else 403

    for method, url in [
        ("get", "/api/admin/users"),
        ("get", f"/api/admin/users/{member}"),
        ("post", f"/api/admin/users/{member}/password-reset"),
        ("post", f"/api/admin/users/{member}/display-name/revert"),
    ]:
        assert getattr(client, method)(url).status_code == expected, url

    client_for(app, "member")  # the password did not change


def test_list_shows_account_data_and_clubs(app, admin, club_id):
    set_user(app, "member", display_name="Анна", email="anna@example.com")
    with app.app_context():
        db.session.get(ClubMember, (club_id, set_user(app, "member"))).banned_at = utcnow()
        db.session.commit()

    users = admin.get("/api/admin/users").get_json()["users"]

    anna = next(u for u in users if u["login"] == "member")
    assert anna["display_name"] == "Анна"
    assert anna["email"] == "anna@example.com"
    assert anna["created_at"]
    assert anna["clubs"] == [
        {"id": club_id, "name": "Tyumen | Speedcubing", "role": "member", "banned": True},
    ]
    org = next(u for u in users if u["login"] == "org")
    assert org["clubs"][0]["role"] == "organizer"


def test_search_by_name_login_and_email(app, admin):
    set_user(app, "member", display_name="Анна Смирнова", email="Cuber@Example.com")

    assert logins(admin, "СМИР") == ["member"]
    assert logins(admin, "MEMB") == ["member"]
    assert logins(admin, "cuber@") == ["member"]
    assert logins(admin, "нет такого") == []


def test_filters(app, admin):
    create_user(app, "kept")
    kept = delete_account(app, "kept", "Сохранённое Имя", keep_name=True)
    create_user(app, "gone")
    delete_account(app, "gone", "Борис", keep_name=False)

    # By name: Админ, Иван Петров (member, org), Сохранённое Имя.
    all_users = admin.get("/api/admin/users").get_json()["users"]
    assert [u["id"] for u in all_users][-1] == kept
    assert len(all_users) == 4  # the fully anonymized account is not listed
    assert logins(admin, filter_name="admins") == ["admin"]
    assert logins(admin, filter_name="organizers") == ["org"]
    deleted = admin.get("/api/admin/users?filter=deleted").get_json()["users"]
    assert [(u["id"], u["display_name"], u["kept_name"]) for u in deleted] == [
        (kept, "Сохранённое Имя", True),
    ]


def test_pages(app, admin, monkeypatch):
    monkeypatch.setattr("app.admin.USERS_PAGE_SIZE", 2)
    set_user(app, "admin", display_name="А")
    set_user(app, "member", display_name="Б")
    set_user(app, "org", display_name="В")

    first = admin.get("/api/admin/users").get_json()
    second = admin.get("/api/admin/users?offset=2").get_json()

    assert [u["login"] for u in first["users"]] == ["admin", "member"]
    assert first["has_more"] is True
    assert [u["login"] for u in second["users"]] == ["org"]
    assert second["has_more"] is False


def test_card_with_consents_and_restrictions(app, admin):
    member = set_user(app, "member")
    me = set_user(app, "admin")

    card = admin.get(f"/api/admin/users/{member}").get_json()["user"]
    own = admin.get(f"/api/admin/users/{me}").get_json()["user"]

    assert set(card["consents"]) == {"processing", "publication", "age"}
    assert card["consents"]["processing"]["accepted_at"]
    assert card["meetups"] == []
    assert card["restrictions"] == {"reset_password": None, "revert_name": "Имя не менялось"}
    assert card["name_history"] == []
    assert own["restrictions"]["reset_password"] == "Свой пароль меняется в профиле"
    assert admin.get("/api/admin/users/999").status_code == 404


@pytest.mark.parametrize("login", ["member", "org"])
def test_reset_password(app, admin, login):
    user_id = set_user(app, login)
    old_session = client_for(app, login)
    assert old_session.get("/api/me/active").status_code == 200

    response = admin.post(f"/api/admin/users/{user_id}/password-reset")

    assert response.status_code == 200
    password = response.get_json()["temporary_password"]
    # The old session no longer works.
    assert old_session.get("/api/me/active").status_code == 401
    # The old password does not work; the temporary one does but requires a change.
    client = app.test_client()
    old = client.post("/api/auth/login", json={"login": login, "password": PASSWORD})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"login": login, "password": password})
    assert new.get_json()["user"]["must_change_password"] is True
    assert error(client.get("/api/me/active"))["code"] == "password_change_required"


def test_reset_password_restrictions(app, admin):
    me = set_user(app, "admin")
    deleted = delete_account(app, "member", "Анна", keep_name=True)

    for user_id in (me, deleted):
        response = admin.post(f"/api/admin/users/{user_id}/password-reset")
        assert response.status_code == 403
        assert error(response)["code"] == "forbidden"
    assert admin.post("/api/admin/users/999/password-reset").status_code == 404
    # The administrator's own session is still there.
    assert admin.get("/api/me/active").status_code == 200
