"""Club page and organizer settings."""

import pytest

from .helpers import MEMBER, ORGANIZER, client_for, create_club, create_user, error


@pytest.fixture
def club_id(app, client):
    club_id = create_club(app)
    create_user(app, "org", ORGANIZER, club_id)
    create_user(app, "member", MEMBER, club_id)
    return club_id


def settings(**overrides):
    data = {
        "name": "Tyumen | Speedcubing",
        "city": "Тюмень",
        "description": "Клуб спидкуберов",
        "logo_color": "teal",
        "links": [
            {"type": "vk", "url": "vk.com/tyumen_speedcubing"},
            {"type": "site", "url": "https://speedcubing-tmn.ru"},
        ],
    }
    data.update(overrides)
    return data


def test_club_page_is_public(app, club_id):
    response = app.test_client().get(f"/api/clubs/{club_id}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["club"]["name"] == "Tyumen | Speedcubing"
    assert body["my_role"] is None


def test_organizer_updates_club(app, club_id):
    org = client_for(app, "org")

    response = org.patch(f"/api/clubs/{club_id}", json=settings())

    assert response.status_code == 200
    club = response.get_json()["club"]
    assert club["logo_color"] == "teal"
    assert club["links"] == [
        {"type": "vk", "url": "https://vk.com/tyumen_speedcubing"},
        {"type": "site", "url": "https://speedcubing-tmn.ru"},
    ]
    # Links are replaced as a whole.
    response = org.patch(f"/api/clubs/{club_id}", json=settings(links=[]))
    assert response.get_json()["club"]["links"] == []


def test_member_cannot_update_club(app, club_id):
    response = client_for(app, "member").patch(f"/api/clubs/{club_id}", json=settings())

    assert response.status_code == 403


def test_guest_cannot_update_club(app, club_id):
    response = app.test_client().patch(f"/api/clubs/{club_id}", json=settings())

    assert response.status_code == 401


@pytest.mark.parametrize("overrides, field", [
    ({"name": ""}, "name"),
    ({"city": " "}, "city"),
    ({"logo_color": "pink"}, "logo_color"),
    ({"links": [{"type": "tiktok", "url": "tiktok.com/x"}]}, "links.0.type"),
    ({"links": [{"type": "vk", "url": "not a link"}]}, "links.0.url"),
    ({"links": [{"type": "vk", "url": "javascript:alert(1)"}]}, "links.0.url"),
])
def test_update_club_checks_fields(app, club_id, overrides, field):
    response = client_for(app, "org").patch(f"/api/clubs/{club_id}", json=settings(**overrides))

    assert response.status_code == 422
    assert list(error(response)["fields"]) == [field]
