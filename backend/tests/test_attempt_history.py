"""Attempt history: entries on creation and edit, history for the organizer, restoring the original."""

from app.extensions import db
from app.models import Attempt, AttemptHistory, Penalty, RecordType

from .helpers import error
from .test_desk import (  # noqa: F401 — fixtures
    attempt_url, desk_row, finish, put, resolve, start_fmc_attempt, summary,
)
from .test_series import (  # noqa: F401 — fixtures
    clients, meetup_id, org, records, results, solve, user_id_of, world,
)


def history_rows(world, series_id, number):
    """Attempt history entries from the DB: [(id, value, penalty, solution, changed_by, changed_at)]."""
    with world["app"].app_context():
        return db.session.execute(
            db.select(
                AttemptHistory.id, AttemptHistory.value, AttemptHistory.penalty,
                AttemptHistory.solution, AttemptHistory.changed_by, AttemptHistory.changed_at,
            )
            .join(Attempt, AttemptHistory.attempt_id == Attempt.id)
            .where(Attempt.series_id == series_id, Attempt.attempt_number == number)
            .order_by(AttemptHistory.changed_at, AttemptHistory.id)
        ).all()


def history(client, meetup_id, user_id, number, event_id="333"):
    return client.get(attempt_url(meetup_id, user_id, number, event_id) + "/history")


def restore(client, meetup_id, user_id, number, version, event_id="333"):
    return client.post(
        attempt_url(meetup_id, user_id, number, event_id) + "/restore", json={"version": version},
    )


# History entries

def test_participant_attempt_writes_first_entry(world, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])

    [entry] = history_rows(world, series["id"], 1)
    assert (entry.value, entry.penalty) == (1000, Penalty.NONE)
    assert entry.changed_by == user_id_of(world, "anna")
    assert "edited" not in series["attempts"][0]


def test_organizer_entry_is_original_not_edit(world, org, meetup_id):
    boris = user_id_of(world, "boris")

    response = put(org, meetup_id, boris, 1, 1234)

    series = desk_row(response, boris)["series"]
    [entry] = history_rows(world, series["id"], 1)
    assert entry.changed_by == user_id_of(world, "org")
    assert "edited" not in series["attempts"][0]


def test_edit_appends_entry_and_keeps_previous(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")
    [first] = history_rows(world, series["id"], 1)

    response = put(org, meetup_id, anna, 1, 1000, "plus2", series["version"])
    version = desk_row(response, anna)["series"]["version"]
    put(org, meetup_id, anna, 1, None, "dnf", version)

    rows = history_rows(world, series["id"], 1)
    assert rows[0] == first
    assert [(r.value, r.penalty) for r in rows] == [
        (1000, Penalty.NONE), (1000, Penalty.PLUS2), (None, Penalty.DNF),
    ]
    assert [r.changed_by for r in rows[1:]] == [user_id_of(world, "org")] * 2


def test_same_value_does_not_add_entry(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])

    response = put(org, meetup_id, user_id_of(world, "anna"), 1, 1000, version=series["version"])

    assert response.status_code == 200
    assert len(history_rows(world, series["id"], 1)) == 1


def test_finish_dns_and_fmc_resolve_write_entries(world, org, clients, meetup_id):
    fmc_series = start_fmc_attempt(world, clients["anna"], meetup_id, expired=True)
    series = solve(clients["boris"], meetup_id, [1000])
    item = summary(org, meetup_id)["fmc"][0]
    assert resolve(org, meetup_id, item, 2).status_code == 204
    assert finish(org, meetup_id).status_code == 200

    organizer = user_id_of(world, "org")
    [fmc_entry] = history_rows(world, fmc_series, 1)
    assert (fmc_entry.value, fmc_entry.solution, fmc_entry.changed_by) == (2, "F' U'", organizer)
    [dns] = history_rows(world, series["id"], 2)
    assert (dns.penalty, dns.changed_by) == (Penalty.DNS, organizer)


# Mark and history

def test_edited_attempt_shows_original_to_everyone(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    put(org, meetup_id, user_id_of(world, "anna"), 1, 1000, "plus2", series["version"])
    expected = {
        "value": 1000, "penalty": "plus2",
        "edited": True, "original": {"value": 1000, "penalty": "none"},
    }

    assert results(clients["boris"], meetup_id)[0]["attempts"][0] == expected
    mine = clients["anna"].get(f"/api/meetups/{meetup_id}/events/333/series/me").get_json()
    assert mine["series"]["attempts"][0] == {"number": 1, **expected}


def test_history_for_organizer(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")
    put(org, meetup_id, anna, 1, 1000, "plus2", series["version"])

    response = history(org, meetup_id, anna, 1)

    assert response.status_code == 200
    entries = response.get_json()["history"]
    assert [(e["value"], e["penalty"], e["changed_by"]["id"]) for e in entries] == [
        (1000, "none", anna), (1000, "plus2", user_id_of(world, "org")),
    ]
    assert entries[0]["changed_at"].endswith("Z")


def test_history_only_for_organizer(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")

    assert history(clients["anna"], meetup_id, anna, 1).status_code == 403
    assert restore(clients["anna"], meetup_id, anna, 1, series["version"]).status_code == 403
    assert history(org, meetup_id, anna, 2).status_code == 404


# Restoring the original result

def test_restore_original(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")
    response = put(org, meetup_id, anna, 1, None, "dnf", series["version"])
    version = desk_row(response, anna)["series"]["version"]

    response = restore(org, meetup_id, anna, 1, version)

    assert response.status_code == 200, response.get_json()
    attempt = desk_row(response, anna)["series"]["attempts"][0]
    assert (attempt["value"], attempt["penalty"]) == (1000, "none")
    # Restoring is an edit too: it goes to the history and the mark stays.
    assert attempt["edited"] is True
    rows = history_rows(world, series["id"], 1)
    assert [(r.value, r.penalty) for r in rows] == [
        (1000, Penalty.NONE), (None, Penalty.DNF), (1000, Penalty.NONE),
    ]
    assert rows[2].changed_by == user_id_of(world, "org")


def test_restore_recalculates_records(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000] * 5)
    series = solve(clients["boris"], meetup_id, [1100] * 5)
    anna, boris = user_id_of(world, "anna"), user_id_of(world, "boris")
    response = put(org, meetup_id, boris, 1, 900, version=series["version"])
    assert records(world)[RecordType.SINGLE] == (boris, 900)

    restore(org, meetup_id, boris, 1, desk_row(response, boris)["series"]["version"])

    assert records(world)[RecordType.SINGLE] == (anna, 1000)


def test_restore_with_stale_version(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")
    put(org, meetup_id, anna, 1, 1100, version=series["version"])

    response = restore(org, meetup_id, anna, 1, series["version"])

    assert error(response)["code"] == "version_conflict"
    assert desk_row(response, anna)["series"]["attempts"][0]["value"] == 1100
