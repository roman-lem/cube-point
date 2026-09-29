"""Meetup deletion by the administrator: the meetup goes with everything in it, records are recalculated."""

import pytest

from app.extensions import db
from app.models import (
    Attempt, AttemptHistory, Disqualification, FmcAttempt, Meetup, MeetupEvent,
    MeetupParticipant, Scramble, Series,
)

from .helpers import client_for, error
from .test_club_deletion import admin, finish  # noqa: F401 — fixture
from .test_profiles import disqualify, personal_records
from .test_series import (  # noqa: F401 — fixtures
    clients, create_live_meetup, meetup_data, org, records, solve, user_id_of, world,
)

# Everything that belongs to a meetup and the models that lead from it to the meetup.
MEETUP_TABLES = {
    Meetup: [],
    MeetupEvent: [Meetup],
    Scramble: [MeetupEvent, Meetup],
    MeetupParticipant: [Meetup],
    Series: [MeetupEvent, Meetup],
    Attempt: [Series, MeetupEvent, Meetup],
    AttemptHistory: [Attempt, Series, MeetupEvent, Meetup],
    FmcAttempt: [Series, MeetupEvent, Meetup],
    Disqualification: [Meetup],
}


def count_rows(app, meetup_id):
    """{table: number of rows of the meetup}."""
    result = {}
    with app.app_context():
        for model, joins in MEETUP_TABLES.items():
            query = db.select(db.func.count()).select_from(model)
            for parent in joins:
                query = query.join(parent)
            result[model.__tablename__] = db.session.scalar(query.where(Meetup.id == meetup_id))
    return result


def delete_meetup(client, meetup_id):
    return client.delete(f"/api/admin/meetups/{meetup_id}")


@pytest.fixture
def full_meetup(world, org, clients):
    """A finished meetup with data in every table."""
    meetup_id = create_live_meetup(world, org, clients)
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    solve(clients["boris"], meetup_id, [900])
    fmc = solve(clients["boris"], meetup_id, [], event_id="333fm")
    response = clients["boris"].post(
        f"/api/series/{fmc['id']}/fmc/start", json={"attempt_number": 1},
    )
    assert response.status_code == 200, response.get_json()
    disqualify(org, meetup_id, user_id_of(world, "boris"))
    finish(world["app"], meetup_id)
    return meetup_id


def test_deletion_summary(admin, full_meetup):
    response = admin.get(f"/api/admin/meetups/{full_meetup}/deletion")

    assert response.get_json() == {
        # 3 requests (pending too), 2 people with series, 5 + 1 attempts.
        "deletion": {"requests": 3, "participants": 2, "results": 6},
        "delete_restriction": None,
    }


def test_deletes_meetup_with_everything(world, admin, org, clients, full_meetup):
    app = world["app"]
    other = create_live_meetup(world, org, clients, days_ahead=3)
    solve(clients["anna"], other, [800])
    finish(app, other)
    before = count_rows(app, full_meetup)
    assert all(before.values()), before
    other_before = count_rows(app, other)

    response = delete_meetup(admin, full_meetup)

    assert response.status_code == 204
    assert set(count_rows(app, full_meetup).values()) == {0}
    assert count_rows(app, other) == other_before
    # Participants keep their accounts.
    for login in ("anna", "boris", "pending"):
        client_for(app, login)


def test_planned_meetup_can_be_deleted(world, admin, org):
    meetup = org.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data()).get_json()

    assert delete_meetup(admin, meetup["meetup"]["id"]).status_code == 204


def test_live_meetup_cannot_be_deleted(world, admin, org, clients):
    meetup_id = create_live_meetup(world, org, clients)
    solve(clients["anna"], meetup_id, [1000])

    summary = admin.get(f"/api/admin/meetups/{meetup_id}/deletion").get_json()
    response = delete_meetup(admin, meetup_id)

    assert summary["delete_restriction"] == "Идёт встреча — удалить её можно после завершения"
    assert response.status_code == 409
    assert error(response)["code"] == "meetup_live"
    assert count_rows(world["app"], meetup_id)["attempts"] == 1


@pytest.mark.parametrize("login", [None, "org", "anna"])
def test_only_admin_deletes(world, clients, full_meetup, login):
    client = client_for(world["app"], login) if login else world["app"].test_client()
    expected = 401 if login is None else 403

    assert client.get(f"/api/admin/meetups/{full_meetup}/deletion").status_code == expected
    assert delete_meetup(client, full_meetup).status_code == expected
    assert count_rows(world["app"], full_meetup)["attempts"] == 6


def test_unknown_meetup(admin):
    assert delete_meetup(admin, 999).status_code == 404


def test_records_are_recalculated(world, admin, org, clients):
    app = world["app"]
    anna, boris = user_id_of(world, "anna"), user_id_of(world, "boris")
    first = create_live_meetup(world, org, clients)
    solve(clients["anna"], first, [900])
    solve(clients["anna"], first, [500], event_id="222")
    finish(app, first)
    second = create_live_meetup(world, org, clients, days_ahead=3)
    solve(clients["boris"], second, [1000])
    solve(clients["anna"], second, [1200])
    finish(app, second)
    assert records(world)["single"] == (anna, 900)
    assert personal_records(admin, anna)["333"]["single"]["value"] == 900

    assert delete_meetup(admin, first).status_code == 204

    # The club record goes to the best result of the remaining meetup.
    assert records(world)["single"] == (boris, 1000)
    # The event was only at the deleted meetup: no record left.
    assert records(world, "222") == {}
    pbs = personal_records(admin, anna)
    assert pbs["333"]["single"]["value"] == 1200
    assert "222" not in pbs
