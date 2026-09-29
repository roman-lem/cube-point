"""FMC solutions: who sees them, and the organizer does not change the move count."""

import pytest

from app.extensions import db
from app.models import Attempt, AttemptHistory, RecordType

from .helpers import error
from .test_desk import attempt_url, desk_row, finish, put, remove, summary
from .test_series import (  # noqa: F401 — fixtures
    clients, meetup_id, org, records, results, start, user_id_of, world,
)

ANNA_SOLUTION = "F' U' R'"


def submit_fmc(client, meetup_id, solution=ANNA_SOLUTION, value=3):
    """The participant starts, freezes and confirms the only FMC attempt."""
    series = start(client, meetup_id, "333fm").get_json()["series"]
    base = f"/api/series/{series['id']}/fmc"
    client.post(f"{base}/start", json={"attempt_number": 1})
    series = client.post(
        f"{base}/freeze", json={"attempt_number": 1, "solution": solution},
    ).get_json()["series"]
    response = client.post(f"{base}/result", json={
        "attempt_number": 1, "value": value, "penalty": "none",
        "version": series["version"], "solution": solution,
    })
    assert response.status_code == 201, response.get_json()


def fmc_row(client, meetup_id, user_id):
    return next(r for r in results(client, meetup_id, "333fm") if r["user"]["id"] == user_id)


def profile_attempt(client, user_id):
    meetups = client.get(f"/api/users/{user_id}/meetups").get_json()["meetups"]
    event = next(e for e in meetups[0]["events"] if e["event_id"] == "333fm")
    return event["attempts"][0]


def desk_fmc_row(org, meetup_id, user_id):
    events = org.get(f"/api/meetups/{meetup_id}/desk").get_json()["events"]
    event = next(e for e in events if e["event_id"] == "333fm")
    return next(r for r in event["rows"] if r["user"]["id"] == user_id)


def history(org, meetup_id, user_id):
    response = org.get(f"{attempt_url(meetup_id, user_id, 1, '333fm')}/history")
    assert response.status_code == 200
    return response.get_json()["history"]


@pytest.fixture
def anna(world, clients, meetup_id):
    submit_fmc(clients["anna"], meetup_id)
    return user_id_of(world, "anna")


# Who sees solutions

def test_solution_hidden_from_others_during_meetup(world, org, clients, meetup_id, anna):
    guest = world["app"].test_client()
    for client in (guest, clients["boris"], org):
        assert "solution" not in fmc_row(client, meetup_id, anna)["attempts"][0]
        assert "solution" not in profile_attempt(client, anna)
    # The organizer does not see it on the desk and in the history either.
    assert "solution" not in desk_fmc_row(org, meetup_id, anna)["series"]["attempts"][0]
    assert [entry["solution"] for entry in history(org, meetup_id, anna)] == [None]


def test_own_solution_always_visible(clients, meetup_id, anna):
    me = clients["anna"]
    assert fmc_row(me, meetup_id, anna)["attempts"][0]["solution"] == ANNA_SOLUTION
    assert profile_attempt(me, anna)["solution"] == ANNA_SOLUTION
    series = me.get(f"/api/meetups/{meetup_id}/events/333fm/series/me").get_json()["series"]
    assert series["attempts"][0]["solution"] == ANNA_SOLUTION


def test_organizer_sees_own_solution(world, org, meetup_id):
    """An organizer taking part in FMC sees their own solution like any participant."""
    org_id = user_id_of(world, "org")
    assert org.post(
        f"/api/meetups/{meetup_id}/participants", json={"user_id": org_id},
    ).status_code in (200, 201)
    submit_fmc(org, meetup_id, solution="R U")

    assert desk_fmc_row(org, meetup_id, org_id)["series"]["attempts"][0]["solution"] == "R U"
    assert fmc_row(org, meetup_id, org_id)["attempts"][0]["solution"] == "R U"


def test_solutions_public_after_finish(world, org, clients, meetup_id, anna):
    assert finish(org, meetup_id).status_code == 200

    guest = world["app"].test_client()
    for client in (guest, clients["boris"], org):
        assert fmc_row(client, meetup_id, anna)["attempts"][0]["solution"] == ANNA_SOLUTION
        assert profile_attempt(client, anna)["solution"] == ANNA_SOLUTION
    assert desk_fmc_row(org, meetup_id, anna)["series"]["attempts"][0]["solution"] == ANNA_SOLUTION
    assert [entry["solution"] for entry in history(org, meetup_id, anna)] == [ANNA_SOLUTION]


def test_finish_dialog_shows_frozen_solution(world, org, clients, meetup_id):
    """The only exception: frozen but unconfirmed attempts in the finish dialog."""
    series = start(clients["boris"], meetup_id, "333fm").get_json()["series"]
    base = f"/api/series/{series['id']}/fmc"
    clients["boris"].post(f"{base}/start", json={"attempt_number": 1})
    clients["boris"].post(f"{base}/freeze", json={"attempt_number": 1, "solution": "R U"})

    item = summary(org, meetup_id)["fmc"][0]
    assert (item["state"], item["solution"]) == ("frozen", "R U")
    # Elsewhere the frozen solution is not given out: it is not an attempt yet.
    assert fmc_row(org, meetup_id, user_id_of(world, "boris"))["attempts"] == [None]


# The organizer does not change the move count

def version_of(org, meetup_id, user_id):
    return desk_fmc_row(org, meetup_id, user_id)["series"]["version"]


def fmc_put(org, meetup_id, user_id, value, penalty, **extra):
    version = version_of(org, meetup_id, user_id)
    return put(org, meetup_id, user_id, 1, value, penalty, version, event_id="333fm", **extra)


@pytest.mark.parametrize("value,penalty", [(4, "none"), (2, "none"), (None, "dns"), (4, "dnf")])
def test_organizer_cannot_change_moves(world, org, meetup_id, anna, value, penalty):
    response = fmc_put(org, meetup_id, anna, value, penalty)

    assert error(response)["code"] == "fmc_locked"
    with world["app"].app_context():
        attempt = db.session.scalar(db.select(Attempt))
        assert (attempt.value, attempt.penalty.value) == (3, "none")
        assert db.session.scalar(db.select(db.func.count(AttemptHistory.id))) == 1


def test_organizer_cannot_erase_fmc_attempt(org, meetup_id, anna):
    response = remove(org, meetup_id, anna, 1, version_of(org, meetup_id, anna), "333fm")
    assert error(response)["code"] == "fmc_locked"


def test_dnf_and_restore(world, org, meetup_id, anna):
    assert records(world, "333fm")[RecordType.SINGLE] == (anna, 3)

    response = fmc_put(org, meetup_id, anna, 3, "dnf")

    assert response.status_code == 200, response.get_json()
    attempt = desk_row(response, anna)["series"]["attempts"][0]
    assert (attempt["value"], attempt["penalty"], attempt["edited"]) == (3, "dnf", True)
    assert RecordType.SINGLE not in records(world, "333fm")
    entries = history(org, meetup_id, anna)
    assert [(e["value"], e["penalty"]) for e in entries] == [(3, "none"), (3, "dnf")]
    # Back from DNF only through the original result, not by entering moves.
    assert error(fmc_put(org, meetup_id, anna, 3, "none"))["code"] == "fmc_locked"

    restore = org.post(
        f"{attempt_url(meetup_id, anna, 1, '333fm')}/restore",
        json={"version": version_of(org, meetup_id, anna)},
    )

    assert restore.status_code == 200
    attempt = desk_row(restore, anna)["series"]["attempts"][0]
    assert (attempt["value"], attempt["penalty"]) == (3, "none")
    assert records(world, "333fm")[RecordType.SINGLE] == (anna, 3)
    assert len(history(org, meetup_id, anna)) == 3
    with world["app"].app_context():
        assert db.session.scalar(db.select(Attempt)).solution == ANNA_SOLUTION


def test_dnf_after_finish(org, meetup_id, anna):
    """Corrections after finishing follow the same rule."""
    assert finish(org, meetup_id).status_code == 200
    assert error(fmc_put(org, meetup_id, anna, 5, "none"))["code"] == "fmc_locked"
    assert fmc_put(org, meetup_id, anna, None, "dnf").status_code == 200


def test_solution_in_request_is_ignored(world, org, meetup_id, anna):
    assert fmc_put(org, meetup_id, anna, 3, "dnf", solution="R").status_code == 200
    with world["app"].app_context():
        assert db.session.scalar(db.select(Attempt)).solution == ANNA_SOLUTION
