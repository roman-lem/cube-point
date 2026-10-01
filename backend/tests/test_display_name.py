"""Display name change by the user, the history and the administrator's revert (app/names.py)."""

from datetime import timedelta

import pytest

from app.extensions import db
from app.models import Club, DisplayNameChange, User

from .helpers import MEMBER, ORGANIZER, PASSWORD, client_for, create_club, create_user, error


@pytest.fixture
def world(app, client):
    club_id = create_club(app)
    with app.app_context():
        other = Club(name="Другой клуб", city="Курган", timezone="Asia/Yekaterinburg")
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    ids = {
        "org": create_user(app, "org", ORGANIZER, club_id),
        "anna": create_user(app, "anna", MEMBER, club_id),
        "boris": create_user(app, "boris", MEMBER, club_id),
        "other_org": create_user(app, "other_org", ORGANIZER, other_id),
        "admin": create_user(app, "admin"),
    }
    with app.app_context():
        db.session.get(User, ids["admin"]).is_admin = True
        db.session.commit()
    return {"app": app, "club_id": club_id, "ids": ids}


def rename(client, name):
    return client.post("/api/auth/display-name", json={"display_name": name})


def name_of(app, user_id):
    with app.app_context():
        return db.session.get(User, user_id).display_name


def age_changes(app, delta):
    with app.app_context():
        for row in db.session.scalars(db.select(DisplayNameChange)):
            row.changed_at -= delta
        db.session.commit()


def revert(client, user_id):
    return client.post(f"/api/admin/users/{user_id}/display-name/revert")


def member_card(client, world, login):
    return client.get(f"/api/clubs/{world['club_id']}/members/{world['ids'][login]}")


# Change by the user

def test_change_name(world):
    app = world["app"]
    anna = client_for(app, "anna")

    response = rename(anna, "  Анна   Смирнова ")

    assert response.status_code == 200
    user = response.get_json()["user"]
    assert user["display_name"] == "Анна Смирнова"
    assert user["display_name_change_available_at"]
    assert name_of(app, world["ids"]["anna"]) == "Анна Смирнова"
    # The new name is shown everywhere: it lives only in users.display_name.
    profile = app.test_client().get(f"/api/users/{world['ids']['anna']}").get_json()
    assert "Анна Смирнова" in str(profile)


def test_me_without_changes_allows_change(world):
    me = client_for(world["app"], "anna").get("/api/auth/me").get_json()["user"]
    assert me["display_name_change_available_at"] is None


@pytest.mark.parametrize("name, message", [
    ("", "Введите имя или никнейм"),
    ("А", "От 2 до 100 символов"),
    ("Анна<script>", "Буквы, цифры, пробел и символы - ' _ ."),
    ("12345", "Нужна хотя бы одна буква"),
    ("Удалённый участник", "Это имя занято"),
    ("Иван Петров", "Это ваше текущее имя"),
])
def test_name_is_validated(world, name, message):
    response = rename(client_for(world["app"], "anna"), name)

    assert response.status_code == 422
    assert error(response)["fields"] == {"display_name": message}


def test_change_once_in_30_days(world):
    app = world["app"]
    anna = client_for(app, "anna")
    rename(anna, "Анна")

    response = rename(anna, "Аня")
    assert response.status_code == 409
    assert error(response)["code"] == "name_change_too_soon"
    assert error(response)["available_at"]
    assert name_of(app, world["ids"]["anna"]) == "Анна"

    age_changes(app, timedelta(days=29, hours=23))
    assert rename(anna, "Аня").status_code == 409
    age_changes(app, timedelta(hours=1))
    assert rename(anna, "Аня").status_code == 200


def test_guest_cannot_change(world):
    assert rename(world["app"].test_client(), "Гость").status_code == 401


# History

def test_history_newest_first(world):
    app = world["app"]
    anna = client_for(app, "anna")
    rename(anna, "Анна")
    age_changes(app, timedelta(days=30))
    rename(anna, "Аня")

    history = member_card(client_for(app, "org"), world, "anna").get_json()["member"]["name_history"]

    assert [(h["old_name"], h["new_name"], h["by_admin"]) for h in history] == [
        ("Анна", "Аня", False), ("Иван Петров", "Анна", False),
    ]
    assert all(h["changed_at"] for h in history)


def test_history_access(world):
    """Only the administrator and the organizers of the user's clubs see the history."""
    app = world["app"]
    rename(client_for(app, "anna"), "Анна")

    assert member_card(client_for(app, "org"), world, "anna").status_code == 200
    assert member_card(client_for(app, "admin"), world, "anna").status_code == 200
    assert member_card(client_for(app, "other_org"), world, "anna").status_code == 403
    assert member_card(client_for(app, "boris"), world, "anna").status_code == 403
    assert member_card(app.test_client(), world, "anna").status_code == 401

    admin_card = client_for(app, "admin").get(f"/api/admin/users/{world['ids']['anna']}")
    assert admin_card.get_json()["user"]["name_history"][0]["new_name"] == "Анна"
    for login in ("org", "anna"):
        response = client_for(app, login).get(f"/api/admin/users/{world['ids']['anna']}")
        assert response.status_code == 403

    # Public pages do not show former names.
    profile = app.test_client().get(f"/api/users/{world['ids']['anna']}").get_json()
    assert "Иван Петров" not in str(profile)
    members = client_for(app, "boris").get(f"/api/clubs/{world['club_id']}/members").get_json()
    assert "name_history" not in str(members)


# The administrator's revert

def test_admin_reverts_name_without_resetting_limit(world):
    app = world["app"]
    anna = client_for(app, "anna")
    rename(anna, "Плохое Имя")

    response = revert(client_for(app, "admin"), world["ids"]["anna"])

    assert response.status_code == 200
    assert response.get_json()["display_name"] == "Иван Петров"
    assert name_of(app, world["ids"]["anna"]) == "Иван Петров"
    history = response.get_json()["name_history"]
    assert (history[0]["old_name"], history[0]["new_name"], history[0]["by_admin"]) == (
        "Плохое Имя", "Иван Петров", True,
    )
    # The user's limit still counts from their own change.
    assert rename(anna, "Другое Имя").status_code == 409
    age_changes(app, timedelta(days=30))
    assert rename(anna, "Другое Имя").status_code == 200


def test_revert_restrictions(world):
    app = world["app"]
    admin = client_for(app, "admin")
    card = admin.get(f"/api/admin/users/{world['ids']['anna']}").get_json()["user"]
    assert card["restrictions"]["revert_name"] == "Имя не менялось"
    assert revert(admin, world["ids"]["anna"]).status_code == 409
    assert revert(admin, 999).status_code == 404


def test_deleted_account_keeps_name_and_loses_history(world):
    """A deleted account with a kept name does not change it; the history is deleted."""
    app = world["app"]
    anna = client_for(app, "anna")
    rename(anna, "Анна")
    anna.post("/api/auth/delete-account", json={"password": PASSWORD, "keep_name": True})

    with app.app_context():
        assert db.session.scalars(db.select(DisplayNameChange)).all() == []
    assert rename(anna, "Новое Имя").status_code == 401
    admin = client_for(app, "admin")
    assert revert(admin, world["ids"]["anna"]).status_code == 409
    assert name_of(app, world["ids"]["anna"]) == "Анна"
