"""Публичные страницы: рекорды клуба, список участников и профиль участника."""

import pytest

from app import profiles

from .helpers import ORGANIZER, client_for, create_club, create_user
from .test_series import (  # noqa: F401 — фикстуры
    clients, create_live_meetup, meetup_id, org, solve, user_id_of, world,
)


def get_json(client, url):
    response = client.get(url)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def club_records(client, world):
    records = get_json(client, f"/api/clubs/{world['club_id']}/records")["records"]
    return {r["event_id"]: r for r in records}


def profile(client, user_id):
    return get_json(client, f"/api/users/{user_id}")


def personal_records(client, user_id):
    return {r["event_id"]: r for r in profile(client, user_id)["personal_records"]}


def history(client, user_id, offset=0):
    return get_json(client, f"/api/users/{user_id}/meetups?offset={offset}")


def members(client, world):
    return get_json(client, f"/api/clubs/{world['club_id']}/members")["members"]


def disqualify(org, meetup_id, user_id):
    response = org.put(
        f"/api/meetups/{meetup_id}/participants/{user_id}/disqualification",
        json={"reason": "Сборка не по скрамблу"},
    )
    assert response.status_code == 200, response.get_json()


def other_club(world, clients):
    """Второй клуб со своим организатором и идущей встречей, где anna и boris подтверждены."""
    app = world["app"]
    club_id = create_club(app)
    create_user(app, "org2", ORGANIZER, club_id)
    other = {"app": app, "club_id": club_id}
    return other, create_live_meetup(other, client_for(app, "org2"), clients)


# Рекорды клуба

def test_club_records_are_public(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    solve(clients["anna"], meetup_id, [800, 900, 700], event_id="222")

    records = club_records(world["app"].test_client(), world)

    assert list(records) == ["333", "222"]
    single = records["333"]["single"]
    assert single["value"] == 1000
    assert single["user"] == {"id": anna, "display_name": "Иван Петров", "has_profile": True}
    assert single["meetup"]["id"] == meetup_id
    assert records["333"]["average"]["value"] == 1200


def test_best_of_formats_have_no_average(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [800, 900, 700], event_id="222")

    assert club_records(clients["anna"], world)["222"]["average"] is None
    assert personal_records(clients["anna"], anna)["222"]["average"] is None
    assert personal_records(clients["anna"], anna)["222"]["single"]["value"] == 700


def test_records_exclude_disqualified(world, org, clients, meetup_id):
    anna, boris = user_id_of(world, "anna"), user_id_of(world, "boris")
    solve(clients["anna"], meetup_id, [900])
    solve(clients["boris"], meetup_id, [1000])

    disqualify(org, meetup_id, anna)

    assert club_records(org, world)["333"]["single"]["user"]["id"] == boris
    assert "333" not in personal_records(org, anna)
    assert profile(org, anna)["meetups_count"] == 0
    assert history(org, anna)["meetups"] == []

    org.delete(f"/api/meetups/{meetup_id}/participants/{anna}/disqualification")

    assert club_records(org, world)["333"]["single"]["user"]["id"] == anna
    assert personal_records(org, anna)["333"]["single"]["value"] == 900


# Профиль участника

def test_personal_records_count_all_clubs(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000])
    other, other_meetup = other_club(world, clients)
    solve(clients["anna"], other_meetup, [900])

    data = profile(world["app"].test_client(), anna)

    assert data["meetups_count"] == 2
    assert [c["id"] for c in data["clubs"]] == sorted([world["club_id"], other["club_id"]])
    pb = {r["event_id"]: r for r in data["personal_records"]}["333"]["single"]
    assert pb["value"] == 900
    assert pb["meetup"]["club"]["id"] == other["club_id"]
    # Рекорд клуба — только по встречам клуба.
    assert club_records(clients["anna"], world)["333"]["single"]["value"] == 1000


def test_personal_record_without_success_is_empty(world, clients, meetup_id):
    boris = user_id_of(world, "boris")
    solve(clients["boris"], meetup_id, [None, None, None], event_id="222")

    assert personal_records(clients["boris"], boris)["222"] == {
        "event_id": "222", "single": None, "average": None,
    }


def test_history_has_attempts_and_current_marks(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    solve(clients["boris"], meetup_id, [900, 950, 1000, 1050, 1100])

    meetups = history(clients["boris"], anna)["meetups"]

    assert len(meetups) == 1
    event = meetups[0]["events"][0]
    assert event["event_id"] == "333"
    assert event["format"] == "ao5"
    assert event["attempts"][0] == {"value": 1000, "penalty": "none"}
    assert event["average"] == 1200
    # Рекорд клуба у boris, личный рекорд — у anna.
    assert event["marks"] == {"single": ["PB"], "average": ["PB"]}
    boris_event = history(clients["boris"], user_id_of(world, "boris"))["meetups"][0]["events"][0]
    assert boris_event["marks"] == {"single": ["LR", "PB"], "average": ["LR", "PB"]}


def test_history_is_paged(world, org, clients, monkeypatch):
    monkeypatch.setattr(profiles, "PAGE_SIZE", 2)
    anna = user_id_of(world, "anna")
    ids = []
    for days_ahead in (3, 4, 5):
        meetup = create_live_meetup(world, org, clients, days_ahead=days_ahead)
        solve(clients["anna"], meetup, [1000])
        ids.append(meetup)

    first = history(clients["anna"], anna)
    second = history(clients["anna"], anna, offset=2)

    # От новых к старым.
    assert [m["id"] for m in first["meetups"]] == [ids[2], ids[1]]
    assert first["has_more"] is True
    assert [m["id"] for m in second["meetups"]] == [ids[0]]
    assert second["has_more"] is False


def test_unknown_user(world):
    assert world["app"].test_client().get("/api/users/999").status_code == 404


# Публичный список участников

def test_banned_member_hidden_but_record_stays(world, org, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [900])
    response = org.put(
        f"/api/clubs/{world['club_id']}/members/{anna}/ban", json={"reason": "Грубил"},
    )
    assert response.status_code == 200

    guest = world["app"].test_client()
    assert anna not in [m["user"]["id"] for m in members(guest, world)]
    assert club_records(guest, world)["333"]["single"]["user"]["id"] == anna
    # Профиль открыт, клуб из списка клубов пропал.
    assert profile(guest, anna)["clubs"] == []
    anna_row = next(m for m in members(org, world) if m["user"]["id"] == anna)
    assert anna_row["records_count"] == 1


def test_members_list_counts_meetups_and_records(world, clients, meetup_id):
    solve(clients["anna"], meetup_id, [900, 1000, 1100, 1200, 1300])
    solve(clients["boris"], meetup_id, [1000])

    rows = {m["user"]["id"]: m for m in members(world["app"].test_client(), world)}

    anna, boris = rows[user_id_of(world, "anna")], rows[user_id_of(world, "boris")]
    assert (anna["meetups_count"], anna["records_count"]) == (1, 2)
    assert (boris["meetups_count"], boris["records_count"]) == (1, 0)


# Логины

def keys(data):
    if isinstance(data, dict):
        return set(data) | {key for value in data.values() for key in keys(value)}
    if isinstance(data, list):
        return {key for value in data for key in keys(value)}
    return set()


@pytest.mark.parametrize("who", ["guest", "member"])
def test_public_responses_have_no_logins(world, clients, meetup_id, who):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [900])
    client = world["app"].test_client() if who == "guest" else clients["boris"]

    for url in (
        f"/api/clubs/{world['club_id']}/records",
        f"/api/clubs/{world['club_id']}/members",
        f"/api/clubs/{world['club_id']}/members?q=anna",
        f"/api/users/{anna}",
        f"/api/users/{anna}/meetups",
        f"/api/meetups/{meetup_id}/events/333/results",
    ):
        assert "login" not in keys(get_json(client, url)), url
    # Поиск по логину — только у организатора.
    assert members(client, world) and get_json(
        client, f"/api/clubs/{world['club_id']}/members?q=anna",
    )["members"] == []


def test_organizer_sees_logins(world, org):
    assert {m["user"]["login"] for m in members(org, world)} >= {"anna", "boris"}
    found = get_json(org, f"/api/clubs/{world['club_id']}/members?q=anna")["members"]
    assert [m["user"]["login"] for m in found] == ["anna"]

