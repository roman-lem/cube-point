"""Meetup cancellation by the organizer: only before the first result, the meetup stays as "cancelled"."""

from app.extensions import db
from app.models import Meetup, MeetupEvent, MeetupParticipant, MeetupStatus, Scramble, Series

from .helpers import client_for, create_user, error
from .test_club_deletion import finish
from .test_series import (  # noqa: F401 — fixtures
    clients, create_live_meetup, meetup_data, org, solve, start, user_id_of, world,
)


def cancel(client, meetup_id):
    return client.post(f"/api/meetups/{meetup_id}/cancel")


def create_planned_meetup(world, org, clients):
    """A planned meetup where anna has a request."""
    response = org.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())
    meetup = response.get_json()["meetup"]
    clients["anna"].post(f"/api/join/{meetup['join_token']}")
    return meetup


def count(app, model, *joins, meetup_id):
    with app.app_context():
        query = db.select(db.func.count()).select_from(model)
        for parent in joins:
            query = query.join(parent)
        return db.session.scalar(query.where(Meetup.id == meetup_id))


def test_organizer_cancels_planned_meetup(world, org, clients):
    meetup = create_planned_meetup(world, org, clients)

    response = cancel(org, meetup["id"])

    assert response.status_code == 200
    body = response.get_json()["meetup"]
    assert body["status"] == "cancelled"
    assert "join_url" not in body
    assert body["cancel_restriction"] == "Встреча уже отменена"
    # The meetup stays with its events, requests and scrambles are gone.
    app = world["app"]
    assert count(app, MeetupEvent, Meetup, meetup_id=meetup["id"]) == 3
    assert count(app, Scramble, MeetupEvent, Meetup, meetup_id=meetup["id"]) == 0
    assert count(app, MeetupParticipant, Meetup, meetup_id=meetup["id"]) == 0


def test_join_link_is_invalid_after_cancelling(world, org, clients):
    meetup = create_planned_meetup(world, org, clients)
    cancel(org, meetup["id"])

    preview = clients["boris"].get(f"/api/join/{meetup['join_token']}")
    joined = clients["boris"].post(f"/api/join/{meetup['join_token']}")

    assert preview.status_code == 404
    assert joined.status_code == 404
    assert error(joined)["code"] == "invalid_link"


def test_live_meetup_without_attempts_can_be_cancelled(world, org, clients):
    meetup_id = create_live_meetup(world, org, clients)
    # A started series without attempts does not block cancelling and is deleted.
    assert start(clients["anna"], meetup_id).status_code == 201

    page = org.get(f"/api/meetups/{meetup_id}").get_json()["meetup"]
    response = cancel(org, meetup_id)

    assert page["cancel_restriction"] is None
    assert response.status_code == 200
    assert count(world["app"], Series, MeetupEvent, Meetup, meetup_id=meetup_id) == 0


def test_cannot_cancel_after_attempt(world, org, clients):
    meetup_id = create_live_meetup(world, org, clients)
    solve(clients["anna"], meetup_id, [1000])

    page = org.get(f"/api/meetups/{meetup_id}").get_json()["meetup"]
    response = cancel(org, meetup_id)

    assert page["cancel_restriction"] == "Участники уже сдали попытки"
    assert response.status_code == 409
    assert error(response)["code"] == "cannot_cancel"
    with world["app"].app_context():
        assert db.session.get(Meetup, meetup_id).status == MeetupStatus.LIVE


def test_cannot_cancel_after_fmc_start(world, org, clients):
    meetup_id = create_live_meetup(world, org, clients)
    series = start(clients["anna"], meetup_id, "333fm").get_json()["series"]
    clients["anna"].post(f"/api/series/{series['id']}/fmc/start", json={"attempt_number": 1})

    response = cancel(org, meetup_id)

    assert response.status_code == 409
    assert error(response)["message"] == "Участники уже начали попытки FMC"


def test_cannot_cancel_finished_or_cancelled_meetup(world, org, clients):
    finished_id = create_live_meetup(world, org, clients)
    finish(world["app"], finished_id)
    cancelled = create_planned_meetup(world, org, clients)
    cancel(org, cancelled["id"])

    assert cancel(org, finished_id).status_code == 409
    assert cancel(org, cancelled["id"]).status_code == 409


def test_member_cannot_cancel(world, org, clients):
    meetup = create_planned_meetup(world, org, clients)

    assert cancel(clients["anna"], meetup["id"]).status_code == 403
    create_user(world["app"], "stranger")
    assert cancel(client_for(world["app"], "stranger"), meetup["id"]).status_code == 403


def test_cancelled_meetup_is_closed(world, org, clients):
    meetup = create_planned_meetup(world, org, clients)
    cancel(org, meetup["id"])
    meetup_id = meetup["id"]
    anna = user_id_of(world, "anna")

    assert org.post(f"/api/meetups/{meetup_id}/start").status_code == 409
    assert org.post(f"/api/meetups/{meetup_id}/token").status_code == 409
    added = org.post(f"/api/meetups/{meetup_id}/participants", json={"user_id": anna})
    assert added.status_code == 409
    assert error(added)["code"] == "meetup_cancelled"
    entered = org.put(
        f"/api/meetups/{meetup_id}/events/333/participants/{anna}/attempts/1",
        json={"value": 1000, "penalty": "none", "version": None},
    )
    assert entered.status_code == 409


def test_cancelled_meetup_is_not_counted_in_club_list(world, org, clients):
    meetup = create_planned_meetup(world, org, clients)
    with world["app"].app_context():
        db.session.get(Meetup, meetup["id"]).status = MeetupStatus.LIVE
        db.session.commit()
    org.post(f"/api/meetups/{meetup['id']}/cancel")

    club = next(
        c for c in org.get("/api/clubs").get_json()["clubs"] if c["id"] == world["club_id"]
    )

    assert club["meetup_count"] == 0
    assert club["last_meetup_date"] is None
