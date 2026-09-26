"""Administration: clubs, organizers, names of deleted accounts and flask make-admin."""

import pytest
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import DELETED_USER_NAME, Club, ClubMember, ClubRole, ConsentType, User, UserConsent

from .helpers import MEMBER, ORGANIZER, PASSWORD, client_for, create_club, create_user, error


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
        db.session.get(User, user_id).is_admin = True
        db.session.commit()
    return client_for(app, "admin")


def new_club(**overrides):
    data = {"name": "Speedcubing Omsk", "city": "Омск", "organizer_login": "member"}
    data.update(overrides)
    return data


def roles(app, club_id):
    with app.app_context():
        members = db.session.scalars(
            db.select(ClubMember).where(ClubMember.club_id == club_id)
        ).all()
        return {m.user.login: m.role for m in members}


def user_id(app, login):
    with app.app_context():
        return db.session.scalar(db.select(User.id).where(User.login == login))


def admin_requests(club_id):
    return [
        ("get", "/api/admin/clubs", None),
        ("get", f"/api/admin/clubs/{club_id}", None),
        ("post", "/api/admin/clubs", new_club()),
        ("post", f"/api/admin/clubs/{club_id}/organizers", {"login": "member"}),
        ("delete", f"/api/admin/clubs/{club_id}/organizers/1", None),
        ("get", "/api/admin/users?q=me", None),
        ("get", "/api/admin/deleted-users", None),
        ("post", "/api/admin/deleted-users/1/anonymize", None),
    ]


@pytest.mark.parametrize("login", [None, "member", "org"])
def test_only_admin_has_access(app, club_id, login):
    client = client_for(app, login) if login else app.test_client()
    expected = 401 if login is None else 403

    for method, url, body in admin_requests(club_id):
        response = getattr(client, method)(url, json=body)
        assert response.status_code == expected, url

    assert roles(app, club_id) == {"org": ORGANIZER, "member": MEMBER}
    with app.app_context():
        assert db.session.query(Club).count() == 1


def test_list_clubs(app, admin, club_id):
    response = admin.get("/api/admin/clubs")

    assert response.status_code == 200
    assert response.get_json()["clubs"] == [{
        "id": club_id, "name": "Tyumen | Speedcubing", "city": "Тюмень",
        "logo_color": "blue", "members_count": 2, "organizers_count": 1,
        "last_meetup_date": None,
    }]


def test_create_club_with_organizer(app, admin):
    response = admin.post("/api/admin/clubs", json=new_club(organizer_login=" Member "))

    assert response.status_code == 201
    club = response.get_json()["club"]
    assert club["timezone"] == "Asia/Yekaterinburg"
    assert [u["login"] for u in club["organizers"]] == ["member"]
    assert roles(app, club["id"]) == {"member": ORGANIZER}


@pytest.mark.parametrize("login", ["", "nobody"])
def test_club_requires_organizer(app, admin, login):
    response = admin.post("/api/admin/clubs", json=new_club(organizer_login=login))

    assert response.status_code == 422
    assert "organizer_login" in error(response)["fields"]
    with app.app_context():
        assert db.session.query(Club).count() == 1


def test_club_timezone_from_iana_list(app, admin):
    response = admin.post("/api/admin/clubs", json=new_club(timezone="Mars/Olympus"))
    assert error(response)["fields"] == {"timezone": "Выберите часовой пояс из списка"}

    response = admin.post("/api/admin/clubs", json=new_club(timezone="Asia/Omsk"))
    assert response.get_json()["club"]["timezone"] == "Asia/Omsk"


def test_add_organizer_promotes_member(app, admin, club_id):
    response = admin.post(f"/api/admin/clubs/{club_id}/organizers", json={"login": "member"})

    assert response.status_code == 200
    assert roles(app, club_id) == {"org": ORGANIZER, "member": ORGANIZER}


def test_add_organizer_twice_makes_no_duplicates(app, admin, club_id):
    create_user(app, "newcomer")

    for _ in range(2):
        response = admin.post(
            f"/api/admin/clubs/{club_id}/organizers", json={"login": "NewComer"},
        )
        assert response.status_code == 200

    assert roles(app, club_id) == {"org": ORGANIZER, "member": MEMBER, "newcomer": ORGANIZER}
    organizers = response.get_json()["club"]["organizers"]
    assert sorted(u["login"] for u in organizers) == ["newcomer", "org"]


def test_add_unknown_or_banned_organizer(app, admin, club_id):
    create_user(app, "banned", MEMBER, club_id, banned=True)
    url = f"/api/admin/clubs/{club_id}/organizers"

    assert error(admin.post(url, json={"login": "nobody"}))["fields"] == {
        "login": "Пользователь не найден",
    }
    response = admin.post(url, json={"login": "banned"})
    assert response.status_code == 409
    assert roles(app, club_id)["banned"] == MEMBER


def test_cannot_remove_last_organizer(app, admin, club_id):
    org_id = user_id(app, "org")

    response = admin.delete(f"/api/admin/clubs/{club_id}/organizers/{org_id}")

    assert response.status_code == 409
    assert error(response)["code"] == "last_organizer"
    assert roles(app, club_id)["org"] == ORGANIZER


def test_removed_organizer_stays_member(app, admin, club_id):
    admin.post(f"/api/admin/clubs/{club_id}/organizers", json={"login": "member"})

    response = admin.delete(f"/api/admin/clubs/{club_id}/organizers/{user_id(app, 'org')}")

    assert response.status_code == 200
    assert roles(app, club_id) == {"org": MEMBER, "member": ORGANIZER}


def test_remove_not_organizer(app, admin, club_id):
    response = admin.delete(f"/api/admin/clubs/{club_id}/organizers/{user_id(app, 'member')}")

    assert response.status_code == 404


def test_search_users_by_login(app, admin):
    response = admin.get("/api/admin/users?q=M")

    assert [u["login"] for u in response.get_json()["users"]] == ["admin", "member"]


# Names of deleted accounts

def delete_account(app, login, name, keep_name):
    uid = user_id(app, login)
    with app.app_context():
        db.session.get(User, uid).display_name = name
        db.session.commit()
    response = client_for(app, login).post(
        "/api/auth/delete-account", json={"password": PASSWORD, "keep_name": keep_name},
    )
    assert response.status_code == 204
    return uid


def deleted_users(admin, query=""):
    response = admin.get(f"/api/admin/deleted-users?q={query}")
    assert response.status_code == 200
    return [(u["id"], u["display_name"]) for u in response.get_json()["users"]]


def test_search_deleted_users_with_kept_name(app, admin):
    anna = delete_account(app, "member", "Анна Смирнова", keep_name=True)
    create_user(app, "boris")
    delete_account(app, "boris", "Борис", keep_name=False)

    assert deleted_users(admin) == [(anna, "Анна Смирнова")]
    # Case-insensitive, Cyrillic included.
    assert deleted_users(admin, "СМИР") == [(anna, "Анна Смирнова")]
    assert deleted_users(admin, "Борис") == []


def test_anonymize_deleted_user(app, admin):
    anna = delete_account(app, "member", "Анна Смирнова", keep_name=True)

    response = admin.post(f"/api/admin/deleted-users/{anna}/anonymize")

    assert response.status_code == 204
    with app.app_context():
        assert db.session.get(User, anna).display_name == DELETED_USER_NAME
        assert db.session.scalars(
            db.select(UserConsent).where(UserConsent.user_id == anna)
        ).all() == []
    assert deleted_users(admin) == []
    # An anonymized account is like a regular deleted one: the profile is open again.
    assert app.test_client().get(f"/api/users/{anna}").status_code == 200


def test_anonymize_only_deleted_with_kept_name(app, admin):
    member = user_id(app, "member")
    create_user(app, "boris")
    boris = delete_account(app, "boris", "Борис", keep_name=False)

    for target in (member, boris, 999):
        response = admin.post(f"/api/admin/deleted-users/{target}/anonymize")
        assert response.status_code == 404
    with app.app_context():
        assert db.session.get(User, member).display_name == "Иван Петров"
        assert db.session.scalars(
            db.select(UserConsent.type).where(UserConsent.user_id == member)
        ).all() == [ConsentType.PROCESSING, ConsentType.PUBLICATION]


# flask make-admin

def test_make_admin_existing_user(app, client):
    create_user(app, "Organizer")

    result = app.test_cli_runner().invoke(args=["make-admin", "ORGANIZER"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db.session.scalar(db.select(User).where(User.login == "organizer")).is_admin


def test_make_admin_creates_user(app, client):
    result = app.test_cli_runner().invoke(
        args=["make-admin", "root"],
        input="Роман Лемур\nlong-password\nlong-password\n",
    )

    assert result.exit_code == 0, result.output
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.login == "root"))
        assert user.is_admin
        assert user.display_name == "Роман Лемур"
        assert check_password_hash(user.password_hash, "long-password")


def test_make_admin_rejects_short_password(app, client):
    result = app.test_cli_runner().invoke(
        args=["make-admin", "root"], input="Роман Лемур\nshort\nshort\n",
    )

    assert result.exit_code != 0
    with app.app_context():
        assert db.session.query(User).count() == 0
