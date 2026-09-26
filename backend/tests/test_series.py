"""Series and attempts: start, attempt order, versions, club records and event table."""

from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import (
    Attempt, ClubRecord, Disqualification, Meetup, MeetupStatus, RecordType, User,
)

from .helpers import MEMBER, ORGANIZER, client_for, create_club, create_user, error

SCRAMBLES = [f"R U{n}" for n in range(1, 6)]


def meetup_data(days_ahead=2):
    return {
        "date": (date.today() + timedelta(days=days_ahead)).isoformat(),
        "starts_at": "18:00",
        "place": "Антикафе «Куб»",
        "events": [
            {"event_id": "333", "format": "ao5", "scrambles": SCRAMBLES},
            {"event_id": "222", "format": "bo3", "scrambles": SCRAMBLES[:3]},
            {"event_id": "333fm", "format": "bo1", "scrambles": ["R' U' F"]},
        ],
    }


@pytest.fixture
def world(app, client):
    club_id = create_club(app)
    create_user(app, "org", ORGANIZER, club_id)
    for login in ("anna", "boris", "pending"):
        create_user(app, login, MEMBER, club_id)
    return {"app": app, "club_id": club_id}


@pytest.fixture
def org(world):
    return client_for(world["app"], "org")


@pytest.fixture
def clients(world):
    return {login: client_for(world["app"], login) for login in ("anna", "boris", "pending")}


def create_live_meetup(world, org, clients, days_ahead=2):
    """A live meetup where anna and boris are approved and pending is waiting."""
    response = org.post(
        f"/api/clubs/{world['club_id']}/meetups", json=meetup_data(days_ahead),
    )
    meetup = response.get_json()["meetup"]
    for login, client in clients.items():
        client.post(f"/api/join/{meetup['join_token']}")
        if login != "pending":
            user_id = user_id_of(world, login)
            org.post(f"/api/meetups/{meetup['id']}/requests/{user_id}/approve")
    assert org.post(f"/api/meetups/{meetup['id']}/start").status_code == 200
    return meetup["id"]


@pytest.fixture
def meetup_id(world, org, clients):
    return create_live_meetup(world, org, clients)


def user_id_of(world, login):
    with world["app"].app_context():
        return db.session.scalar(db.select(User.id).where(User.login == login))


def start(client, meetup_id, event_id="333"):
    return client.post(f"/api/meetups/{meetup_id}/events/{event_id}/series")


def submit(client, series, value, penalty="none", number=None, version=None):
    return client.post(f"/api/series/{series['id']}/attempts", json={
        "attempt_number": number or len(series["attempts"]) + 1,
        "value": value,
        "penalty": penalty,
        "version": series["version"] if version is None else version,
    })


def solve(client, meetup_id, values, event_id="333"):
    """Starts a series and submits attempts in order. Returns the series."""
    series = start(client, meetup_id, event_id).get_json()["series"]
    for value in values:
        penalty = "dnf" if value is None else "none"
        response = submit(client, series, value, penalty)
        assert response.status_code == 201, response.get_json()
        series = response.get_json()["series"]
    return series


def records(world, event_id="333"):
    with world["app"].app_context():
        return {
            r.type: (r.user_id, r.value)
            for r in db.session.scalars(db.select(ClubRecord).where(
                ClubRecord.event_id == event_id,
            ))
        }


def results(client, meetup_id, event_id="333"):
    response = client.get(f"/api/meetups/{meetup_id}/events/{event_id}/results")
    assert response.status_code == 200
    return response.get_json()["rows"]


# Starting a series

def test_approved_participant_starts_series(clients, meetup_id):
    response = start(clients["anna"], meetup_id)

    assert response.status_code == 201
    series = response.get_json()["series"]
    assert series["status"] == "in_progress"
    assert series["attempts"] == []
    assert series["next_attempt"] == {"number": 1, "scramble": SCRAMBLES[0]}


def test_pending_participant_cannot_start_series(clients, meetup_id):
    response = start(clients["pending"], meetup_id)

    assert response.status_code == 403
    assert error(response)["code"] == "not_approved"


def test_stranger_cannot_start_series(world, meetup_id):
    create_user(world["app"], "stranger")

    response = start(client_for(world["app"], "stranger"), meetup_id)

    assert response.status_code == 403


def test_second_series_in_same_event_is_rejected(clients, meetup_id):
    start(clients["anna"], meetup_id)

    response = start(clients["anna"], meetup_id)

    assert response.status_code == 409
    assert error(response)["code"] == "series_exists"


def test_series_can_run_in_several_events_at_once(clients, meetup_id):
    assert start(clients["anna"], meetup_id, "333").status_code == 201
    assert start(clients["anna"], meetup_id, "222").status_code == 201


def test_series_cannot_start_before_meetup_is_live(world, org, clients):
    response = org.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())
    meetup = response.get_json()["meetup"]
    clients["anna"].post(f"/api/join/{meetup['join_token']}")
    org.post(f"/api/meetups/{meetup['id']}/requests/{user_id_of(world, 'anna')}/approve")

    response = start(clients["anna"], meetup["id"])

    assert response.status_code == 409
    assert error(response)["code"] == "meetup_not_live"


def test_disqualified_cannot_start_series(world, clients, meetup_id):
    with world["app"].app_context():
        db.session.add(Disqualification(
            meetup_id=meetup_id, user_id=user_id_of(world, "anna"), reason="Тест",
        ))
        db.session.commit()

    response = start(clients["anna"], meetup_id)

    assert response.status_code == 403
    assert error(response)["code"] == "disqualified"


def test_unknown_event(clients, meetup_id):
    assert start(clients["anna"], meetup_id, "444").status_code == 404


# Attempts

def test_only_current_scramble_is_given(clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000, 1100])

    assert series["next_attempt"] == {"number": 3, "scramble": SCRAMBLES[2]}
    assert "scrambles" not in series
    response = clients["anna"].get(f"/api/meetups/{meetup_id}/events/333/series/me")
    assert response.get_json()["series"]["next_attempt"]["scramble"] == SCRAMBLES[2]


def test_attempt_out_of_order_is_rejected(clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])

    skipped = submit(clients["anna"], series, 1100, number=3)
    repeated = submit(clients["anna"], series, 1100, number=1)

    assert skipped.status_code == 409
    assert error(skipped)["code"] == "wrong_attempt_number"
    # A participant does not change a saved attempt.
    assert repeated.status_code == 409
    assert error(repeated)["code"] == "wrong_attempt_number"


def test_version_conflict(clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])

    response = submit(clients["anna"], series, 1100, version=series["version"] - 1)

    assert response.status_code == 409
    body = error(response)
    assert body["code"] == "version_conflict"
    # The client gets the current series and can retry the save.
    assert body["series"]["version"] == series["version"]
    assert submit(clients["anna"], body["series"], 1100).status_code == 201


def test_version_grows_on_every_save(clients, meetup_id):
    series = start(clients["anna"], meetup_id).get_json()["series"]
    first = submit(clients["anna"], series, 1000).get_json()["series"]
    # The best does not change and there is no average yet, but the version still grows.
    second = submit(clients["anna"], first, 1500).get_json()["series"]

    assert series["version"] < first["version"] < second["version"]


def test_series_completes_after_last_attempt(clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000, 1100, None, 1300, 1200])

    assert series["status"] == "completed"
    assert series["next_attempt"] is None
    assert series["best"] == 1000
    assert series["average"] == 1200
    response = submit(clients["anna"], series, 1000, number=6)
    assert error(response)["code"] == "series_completed"


def test_attempt_is_saved_with_penalty_and_submitter(world, clients, meetup_id):
    series = start(clients["anna"], meetup_id).get_json()["series"]

    series = submit(clients["anna"], series, 1000, penalty="plus2").get_json()["series"]

    assert series["best"] == 1200
    with world["app"].app_context():
        attempt = db.session.scalar(db.select(Attempt))
        assert attempt.entered_by == user_id_of(world, "anna")
        assert attempt.submitted_at is not None


@pytest.mark.parametrize("value, penalty", [
    (1000, "dns"), (0, "none"), (-5, "none"), (None, "none"), (1.5, "none"),
    (True, "none"), (360_000, "none"), (1000, "bad"),
])
def test_invalid_attempt(clients, meetup_id, value, penalty):
    series = start(clients["anna"], meetup_id).get_json()["series"]

    response = submit(clients["anna"], series, value, penalty)

    assert response.status_code == 422


def test_dnf_without_time(clients, meetup_id):
    series = start(clients["anna"], meetup_id).get_json()["series"]

    assert submit(clients["anna"], series, None, "dnf").status_code == 201


def test_cannot_submit_to_someone_elses_series(clients, meetup_id):
    series = start(clients["anna"], meetup_id).get_json()["series"]

    assert submit(clients["boris"], series, 1000).status_code == 403


def test_fmc_attempt_is_not_submitted_as_timed(clients, meetup_id):
    series = start(clients["anna"], meetup_id, "333fm").get_json()["series"]

    response = submit(clients["anna"], series, 30)
    assert response.status_code == 409
    assert error(response)["code"] == "fmc_series"


# Club records

def test_record_moves_to_new_best_result(world, clients, meetup_id):
    anna, boris = user_id_of(world, "anna"), user_id_of(world, "boris")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    assert records(world) == {
        RecordType.SINGLE: (anna, 1000), RecordType.AVERAGE: (anna, 1200),
    }

    solve(clients["boris"], meetup_id, [900, 1000, 1100, 1200, 1300])

    assert records(world) == {
        RecordType.SINGLE: (boris, 900), RecordType.AVERAGE: (boris, 1100),
    }


def test_record_tie_stays_with_first(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])

    solve(clients["boris"], meetup_id, [1000, 1100, 1200, 1300, 1400])

    assert records(world) == {
        RecordType.SINGLE: (anna, 1000), RecordType.AVERAGE: (anna, 1200),
    }


def test_record_tie_goes_to_earlier_meetup(world, org, clients):
    later = create_live_meetup(world, org, clients, days_ahead=5)
    earlier = create_live_meetup(world, org, clients, days_ahead=3)
    # At a later meetup the result was submitted earlier, but the record goes to the earlier date.
    solve(clients["boris"], later, [1000])

    solve(clients["anna"], earlier, [1000])

    assert records(world)[RecordType.SINGLE] == (user_id_of(world, "anna"), 1000)


def test_plus_two_counts_in_record(world, clients, meetup_id):
    series = start(clients["anna"], meetup_id).get_json()["series"]
    submit(clients["anna"], series, 900, penalty="plus2")

    assert records(world)[RecordType.SINGLE] == (user_id_of(world, "anna"), 1100)


def test_disqualified_results_leave_records_and_table(world, clients, meetup_id):
    solve(clients["anna"], meetup_id, [900])
    with world["app"].app_context():
        db.session.add(Disqualification(
            meetup_id=meetup_id, user_id=user_id_of(world, "anna"), reason="Тест",
        ))
        db.session.commit()

    solve(clients["boris"], meetup_id, [1000])

    assert records(world)[RecordType.SINGLE] == (user_id_of(world, "boris"), 1000)
    assert [r["user"]["id"] for r in results(clients["boris"], meetup_id)] == [
        user_id_of(world, "boris"),
    ]


# Event table

def test_results_table_order_and_places(world, org, clients, meetup_id):
    for login in ("vera", "gleb", "dima"):
        create_user(world["app"], login, MEMBER, world["club_id"])
        clients[login] = client_for(world["app"], login)
    meetup = org.get(f"/api/meetups/{meetup_id}").get_json()["meetup"]
    for login in ("vera", "gleb", "dima"):
        clients[login].post(f"/api/join/{meetup['join_token']}")
    org.post(f"/api/meetups/{meetup_id}/requests/approve-all")

    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])   # average 12.00
    solve(clients["boris"], meetup_id, [1400, 1300, 1200, 1100, 1000])  # same, shared place
    solve(clients["vera"], meetup_id, [800, None, None, 900, 900])      # DNF, best 8.00
    solve(clients["gleb"], meetup_id, [None] * 5)                        # all DNF
    solve(clients["dima"], meetup_id, [700])                             # in progress

    rows = results(world["app"].test_client(), meetup_id)

    assert [(r["place"], r["status"], r["best"]) for r in rows] == [
        (1, "completed", 1000),
        (1, "completed", 1000),
        (3, "completed", 800),
        (None, "completed", -1),
        (None, "in_progress", 700),
    ]
    assert rows[2]["average"] == -1
    assert rows[4]["attempts"] == [{"value": 700, "penalty": "none"}, None, None, None, None]


def test_results_table_for_best_of_format(world, clients, meetup_id):
    solve(clients["anna"], meetup_id, [900, None, 1000], event_id="222")
    solve(clients["boris"], meetup_id, [800, 2000, 2100], event_id="222")

    rows = results(clients["anna"], meetup_id, "222")

    assert [(r["place"], r["best"]) for r in rows] == [(1, 800), (2, 900)]


def test_record_marks(world, org, clients, meetup_id):
    # Anna had 8.00 at another meetup earlier, so today's result is not a PB.
    earlier = create_live_meetup(world, org, clients, days_ahead=1)
    solve(clients["anna"], earlier, [800])
    solve(clients["anna"], meetup_id, [1000, 1000, 1000, 1000, 1000])
    solve(clients["boris"], meetup_id, [900, 1100, 1100, 1100, 1100])

    rows = {r["user"]["id"]: r["marks"] for r in results(clients["anna"], meetup_id)}

    assert rows[user_id_of(world, "anna")] == {"single": [], "average": ["LR", "PB"]}
    # A person's first result is a PB too. The single record is Anna's from the previous meetup.
    assert rows[user_id_of(world, "boris")] == {"single": ["PB"], "average": ["PB"]}


def test_results_are_public(world, meetup_id):
    guest = world["app"].test_client()

    assert guest.get(f"/api/meetups/{meetup_id}/events/333/results").status_code == 200


# Event cards on the meetup page

def test_meetup_page_shows_my_series_and_leader(world, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    solve(clients["boris"], meetup_id, [1500, 1500])

    events = clients["boris"].get(f"/api/meetups/{meetup_id}").get_json()["meetup"]["events"]

    cube = events[0]
    assert cube["leader"] == {"display_name": "Иван Петров", "value": 1200, "is_average": True}
    assert cube["my_series"] == {
        "status": "in_progress", "attempts_done": 2, "best": 1500, "average": None,
        "place": None, "total": 2,
    }
    assert events[1]["my_series"] is None
    assert events[1]["leader"] is None


# Active meetups

def test_my_active_meetups(clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000])

    meetups = clients["anna"].get("/api/me/active").get_json()["meetups"]
    pending = clients["pending"].get("/api/me/active").get_json()["meetups"]

    assert [m["id"] for m in meetups] == [meetup_id]
    assert meetups[0]["events"][0]["series"] == {"status": "in_progress", "attempts_done": 1}
    assert meetups[0]["events"][1]["series"] is None
    assert pending == []


# User's series at live meetups

def test_my_series_on_live_meetups(clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000, None])
    solve(clients["anna"], meetup_id, [900, 1000, 1100], event_id="222")
    solve(clients["boris"], meetup_id, [1500])

    response = clients["anna"].get("/api/me/series")

    assert response.status_code == 200
    meetups = response.get_json()["meetups"]
    assert [m["id"] for m in meetups] == [meetup_id]
    assert meetups[0]["club"]["timezone"]
    cube, two = meetups[0]["series"]
    assert cube == {
        "id": cube["id"], "event_id": "333", "format": "ao5", "status": "in_progress",
        "attempts": [
            {"value": 1000, "penalty": "none"}, {"value": None, "penalty": "dnf"},
            None, None, None,
        ],
        "best": 1000, "average": None,
    }
    assert (two["event_id"], two["status"], two["best"]) == ("222", "completed", 900)


def test_my_series_without_series(clients, meetup_id):
    assert clients["boris"].get("/api/me/series").get_json() == {"meetups": []}


def test_my_series_skips_finished_meetups(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000])
    with world["app"].app_context():
        db.session.get(Meetup, meetup_id).status = MeetupStatus.FINISHED
        db.session.commit()

    assert clients["anna"].get("/api/me/series").get_json() == {"meetups": []}


def test_my_series_requires_login(client):
    assert client.get("/api/me/series").status_code == 401
