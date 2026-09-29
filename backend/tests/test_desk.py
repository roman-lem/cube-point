"""Organizer desk: manual entry and edits, participants, disqualification, finishing."""

from datetime import timedelta

import pytest

from app.events import FMC_TIME_LIMIT
from app.extensions import db
from app.models import Attempt, FmcAttempt, MeetupParticipant, RecordType, User

from .helpers import MEMBER, create_user, error
from .test_series import (  # noqa: F401 — fixtures
    clients, meetup_id, org, records, results, solve, start, submit, user_id_of, world,
)


def attempt_url(meetup_id, user_id, number, event_id="333"):
    return f"/api/meetups/{meetup_id}/events/{event_id}/participants/{user_id}/attempts/{number}"


def put(client, meetup_id, user_id, number, value, penalty="none", version=None, **extra):
    return client.put(
        attempt_url(meetup_id, user_id, number, extra.pop("event_id", "333")),
        json={"value": value, "penalty": penalty, "version": version, **extra},
    )


def desk_row(response, user_id):
    body = response.get_json()
    # On error, fresh event data is inside "error".
    rows = (body.get("event") or body["error"]["event"])["rows"]
    return next(row for row in rows if row["user"]["id"] == user_id)


def saved_attempt(world, series_id, number):
    with world["app"].app_context():
        attempt = db.session.scalar(db.select(Attempt).where(
            Attempt.series_id == series_id, Attempt.attempt_number == number,
        ))
        db.session.expunge(attempt)
        return attempt


# Edits and manual entry

def test_edit_keeps_submitted_at(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000, 1100])
    before = saved_attempt(world, series["id"], 1)
    anna = user_id_of(world, "anna")

    response = put(org, meetup_id, anna, 1, 1000, "plus2", series["version"])

    assert response.status_code == 200, response.get_json()
    after = saved_attempt(world, series["id"], 1)
    assert after.submitted_at == before.submitted_at
    assert after.updated_at is not None
    assert after.entered_by == user_id_of(world, "org")
    assert desk_row(response, anna)["series"]["attempts"][0] == {
        "value": 1000, "penalty": "plus2",
        "edited": True, "original": {"value": 1000, "penalty": "none"},
    }


def test_organizer_and_participant_conflict(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")

    assert submit(clients["anna"], series, 1200).status_code == 201
    response = put(org, meetup_id, anna, 1, 900, version=series["version"])

    assert response.status_code == 409
    assert error(response)["code"] == "version_conflict"
    fresh = desk_row(response, anna)["series"]
    assert [a["value"] for a in fresh["attempts"][:2]] == [1000, 1200]


def test_participant_conflicts_with_organizer(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    anna = user_id_of(world, "anna")

    assert put(org, meetup_id, anna, 1, 1100, version=series["version"]).status_code == 200
    response = submit(clients["anna"], series, 1200)

    assert response.status_code == 409
    assert error(response)["code"] == "version_conflict"


def test_organizer_starts_series_for_participant(world, org, meetup_id):
    boris = user_id_of(world, "boris")

    response = put(org, meetup_id, boris, 1, 1234)

    assert response.status_code == 200, response.get_json()
    series = desk_row(response, boris)["series"]
    assert series["attempts"][0] == {"value": 1234, "penalty": "none"}
    # The next attempt already comes with the series version.
    response = put(org, meetup_id, boris, 2, None, "dns", series["version"])
    assert response.status_code == 200
    assert desk_row(response, boris)["series"]["attempts"][1]["penalty"] == "dns"


def test_new_series_with_version_is_conflict(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000])
    response = put(org, meetup_id, user_id_of(world, "anna"), 2, 1000, version=None)
    assert error(response)["code"] == "version_conflict"


def test_organizer_cannot_skip_attempt(world, org, meetup_id):
    boris = user_id_of(world, "boris")
    assert error(put(org, meetup_id, boris, 2, 1000))["code"] == "wrong_attempt_number"
    series = desk_row(put(org, meetup_id, boris, 1, 1000), boris)["series"]
    response = put(org, meetup_id, boris, 3, 1000, version=series["version"])
    assert error(response)["code"] == "wrong_attempt_number"


def test_not_approved_participant(world, org, meetup_id):
    response = put(org, meetup_id, user_id_of(world, "pending"), 1, 1000)
    assert error(response)["code"] == "not_approved"


@pytest.mark.parametrize("value,penalty", [(0, "none"), (None, "none"), (1000, "bad")])
def test_invalid_organizer_attempt(world, org, meetup_id, value, penalty):
    response = put(org, meetup_id, user_id_of(world, "boris"), 1, value, penalty)
    assert response.status_code == 422


def test_organizer_does_not_add_fmc_attempts(world, org, meetup_id):
    """FMC attempts come from the participant or the finish dialog (test_fmc_solutions.py)."""
    boris = user_id_of(world, "boris")
    assert put(org, meetup_id, boris, 1, 30, "plus2", event_id="333fm").status_code == 422
    assert put(org, meetup_id, boris, 1, 81, event_id="333fm").status_code == 422

    for value, penalty in ((3, "none"), (None, "dnf"), (None, "dns")):
        response = put(org, meetup_id, boris, 1, value, penalty, event_id="333fm")
        assert error(response)["code"] == "fmc_locked"
    with world["app"].app_context():
        assert db.session.scalar(db.select(Attempt)) is None


def test_edit_updates_records(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000] * 5)
    series = solve(clients["boris"], meetup_id, [1100] * 5)
    boris = user_id_of(world, "boris")

    put(org, meetup_id, boris, 1, 900, version=series["version"])

    assert records(world)[RecordType.SINGLE] == (boris, 900)


def remove(client, meetup_id, user_id, number, version, event_id="333"):
    return client.delete(attempt_url(meetup_id, user_id, number, event_id), json={"version": version})


def enter(org, meetup_id, user_id, values):
    """A series entered entirely by the organizer. Returns the series from the entry table."""
    series = None
    for number, value in enumerate(values, 1):
        response = put(org, meetup_id, user_id, number, value, version=series and series["version"])
        series = desk_row(response, user_id)["series"]
    return series


def test_remove_last_attempt(world, org, clients, meetup_id):
    boris = user_id_of(world, "boris")
    series = enter(org, meetup_id, boris, [1000] * 5)
    first = saved_attempt(world, series["id"], 1)

    response = remove(org, meetup_id, boris, 5, series["version"])

    assert response.status_code == 200, response.get_json()
    row = desk_row(response, boris)["series"]
    assert row["status"] == "in_progress"
    assert row["attempts"][4] is None
    assert row["average"] is None
    assert saved_attempt(world, series["id"], 1).submitted_at == first.submitted_at
    # An erased attempt can be entered again.
    assert put(org, meetup_id, boris, 5, 1200, version=row["version"]).status_code == 200


def test_participant_attempt_cannot_be_removed(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000, 1100])
    anna = user_id_of(world, "anna")

    response = remove(org, meetup_id, anna, 2, series["version"])
    assert error(response)["code"] == "participant_attempt"
    # A participant's attempt corrected by the organizer cannot be erased either.
    series = desk_row(put(org, meetup_id, anna, 2, 1200, version=series["version"]), anna)["series"]
    response = remove(org, meetup_id, anna, 2, series["version"])
    assert error(response)["code"] == "participant_attempt"
    assert saved_attempt(world, series["id"], 2).value == 1200


def test_remove_only_last_attempt(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000, 1100])
    response = remove(org, meetup_id, user_id_of(world, "anna"), 1, series["version"])
    assert error(response)["code"] == "not_last_attempt"
    assert "event" in error(response)


def test_remove_single_attempt_deletes_series(world, org, clients, meetup_id):
    boris = user_id_of(world, "boris")
    series = desk_row(put(org, meetup_id, boris, 1, 900), boris)["series"]
    assert records(world)[RecordType.SINGLE] == (boris, 900)

    response = remove(org, meetup_id, boris, 1, series["version"])

    assert desk_row(response, boris)["series"] is None
    assert results(org, meetup_id) == []
    assert records(world) == {}
    # On meetup finish this person will not get DNS.
    assert summary(org, meetup_id)["dns_count"] == 0


def test_remove_with_stale_version(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    submit(clients["anna"], series, 1100)
    response = remove(org, meetup_id, user_id_of(world, "anna"), 1, series["version"])
    assert error(response)["code"] == "version_conflict"


# Finishing a meetup

def finish(org, meetup_id):
    return org.post(f"/api/meetups/{meetup_id}/finish")


def summary(org, meetup_id):
    response = org.get(f"/api/meetups/{meetup_id}/finish-summary")
    assert response.status_code == 200
    return response.get_json()


def test_finish_turns_missing_attempts_into_dns(world, org, clients, meetup_id):
    join_token = org.get(f"/api/meetups/{meetup_id}").get_json()["meetup"]["join_token"]
    solve(clients["anna"], meetup_id, [1000, 1100])
    solve(clients["boris"], meetup_id, [1000] * 5)

    data = summary(org, meetup_id)
    assert data["dns_count"] == 3
    assert [u["user"]["login"] for u in data["unfinished"]] == ["anna"]
    assert data["unfinished"][0]["events"] == [
        {"event_id": "333", "attempts_done": 2, "attempts_count": 5},
    ]

    response = finish(org, meetup_id)

    assert response.status_code == 200
    assert response.get_json()["meetup"]["status"] == "finished"
    anna = next(r for r in results(org, meetup_id) if r["user"]["id"] == user_id_of(world, "anna"))
    assert anna["status"] == "completed"
    assert [a["penalty"] for a in anna["attempts"]] == ["none", "none", "dns", "dns", "dns"]
    assert anna["average"] == -1
    # Series that were not started are not created.
    assert results(org, meetup_id, "222") == []
    # The meetup link no longer works.
    assert clients["pending"].get(f"/api/join/{join_token}").status_code == 404


def test_after_finish_participant_cannot_submit(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000])
    finish(org, meetup_id)

    response = submit(clients["anna"], series, 1000, number=2)
    assert error(response)["code"] == "meetup_not_live"
    assert error(start(clients["boris"], meetup_id))["code"] == "meetup_not_live"


def test_after_finish_organizer_adds_attempts(world, org, meetup_id):
    finish(org, meetup_id)
    boris = user_id_of(world, "boris")

    response = put(org, meetup_id, boris, 1, 1000)

    assert response.status_code == 200
    assert desk_row(response, boris)["series"]["attempts"][0]["value"] == 1000


def test_finish_only_live_meetup(org, meetup_id):
    finish(org, meetup_id)
    assert error(finish(org, meetup_id))["code"] == "meetup_not_live"


def start_fmc_attempt(world, client, meetup_id, expired=False, frozen=None):
    series = start(client, meetup_id, "333fm").get_json()["series"]
    client.post(f"/api/series/{series['id']}/fmc/start", json={"attempt_number": 1})
    client.put(
        f"/api/series/{series['id']}/fmc/draft",
        json={"attempt_number": 1, "solution": "F' U'"},
    )
    if frozen:
        client.post(
            f"/api/series/{series['id']}/fmc/freeze",
            json={"attempt_number": 1, "solution": frozen},
        )
    if expired:
        with world["app"].app_context():
            fmc_attempt = db.session.get(FmcAttempt, (series["id"], 1))
            fmc_attempt.started_at -= FMC_TIME_LIMIT + timedelta(seconds=1)
            db.session.commit()
    return series["id"]


def resolve(org, meetup_id, item, value, penalty="none", solution=None):
    return org.post(
        f"/api/meetups/{meetup_id}/fmc/{item['series_id']}/{item['attempt_number']}/resolve",
        json={
            "value": value, "penalty": penalty, "version": item["version"],
            "solution": item["solution"] if solution is None else solution,
        },
    )


def test_unresolved_fmc_blocks_finish(world, org, clients, meetup_id):
    start_fmc_attempt(world, clients["anna"], meetup_id, frozen="R' U' F'")
    start_fmc_attempt(world, clients["boris"], meetup_id, expired=True)

    data = summary(org, meetup_id)
    states = {i["user"]["login"]: (i["state"], i["solution"]) for i in data["fmc"]}
    assert states == {"anna": ("frozen", "R' U' F'"), "boris": ("expired", "F' U'")}
    assert data["dns_count"] == 0
    assert data["fmc"][0]["scramble"] == "R' U' F"
    assert error(finish(org, meetup_id))["code"] == "fmc_unresolved"

    anna, boris = sorted(data["fmc"], key=lambda i: i["user"]["login"])
    assert resolve(org, meetup_id, anna, 3).status_code == 204
    assert resolve(org, meetup_id, boris, None, "dnf").status_code == 204
    assert finish(org, meetup_id).status_code == 200

    rows = {r["user"]["id"]: r for r in results(org, meetup_id, "333fm")}
    # After finishing, the solutions are public.
    assert rows[user_id_of(world, "anna")]["attempts"] == [
        {"value": 3, "penalty": "none", "solution": "R' U' F'"},
    ]
    assert rows[user_id_of(world, "boris")]["attempts"] == [
        {"value": None, "penalty": "dnf", "solution": "F' U'"},
    ]


def test_resolve_keeps_submission_time_and_solution(world, org, clients, meetup_id):
    series_id = start_fmc_attempt(world, clients["anna"], meetup_id, expired=True)
    item = summary(org, meetup_id)["fmc"][0]

    assert resolve(org, meetup_id, item, 3, solution="R").status_code == 409
    assert resolve(org, meetup_id, item, 2).status_code == 204

    with world["app"].app_context():
        fmc_attempt = db.session.get(FmcAttempt, (series_id, 1))
        deadline = fmc_attempt.started_at + FMC_TIME_LIMIT
    attempt = saved_attempt(world, series_id, 1)
    assert attempt.submitted_at == deadline
    assert attempt.solution == "F' U'"


def test_running_fmc_can_only_be_dnf(world, org, clients, meetup_id):
    series_id = start_fmc_attempt(world, clients["anna"], meetup_id)
    item = summary(org, meetup_id)["fmc"][0]
    assert item["state"] == "running"
    # The draft of a running attempt is not shown: nobody peeks while the hour is on.
    assert item["solution"] is None

    assert error(resolve(org, meetup_id, item, 2))["code"] == "fmc_running"
    assert resolve(org, meetup_id, item, None, "dnf").status_code == 204
    assert summary(org, meetup_id)["fmc"] == []
    # The current draft is kept with the DNF.
    assert saved_attempt(world, series_id, 1).solution == "F' U'"


# Disqualification

def disqualify(org, meetup_id, user_id, reason="Сборка не по скрамблу"):
    return org.put(
        f"/api/meetups/{meetup_id}/participants/{user_id}/disqualification",
        json={"reason": reason},
    )


def test_disqualification_and_cancel_change_records(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [900] * 5)
    solve(clients["boris"], meetup_id, [1100] * 5)
    anna, boris = user_id_of(world, "anna"), user_id_of(world, "boris")
    assert records(world)[RecordType.SINGLE] == (anna, 900)

    response = disqualify(org, meetup_id, anna)

    assert response.status_code == 200
    assert records(world)[RecordType.SINGLE] == (boris, 1100)
    assert [r["user"]["id"] for r in results(org, meetup_id)] == [boris]
    desk = org.get(f"/api/meetups/{meetup_id}/desk").get_json()
    participant = next(p for p in desk["participants"] if p["user"]["id"] == anna)
    assert participant["disqualification"]["reason"] == "Сборка не по скрамблу"

    response = org.delete(f"/api/meetups/{meetup_id}/participants/{anna}/disqualification")

    assert response.status_code == 204
    assert records(world)[RecordType.SINGLE] == (anna, 900)


def test_disqualification_needs_reason(world, org, meetup_id):
    response = disqualify(org, meetup_id, user_id_of(world, "anna"), reason="  ")
    assert error(response)["fields"] == {"reason": "Укажите причину"}


# Participants

def test_add_club_member(world, org, meetup_id):
    create_user(world["app"], "vera", MEMBER, world["club_id"])
    candidates = org.get(f"/api/meetups/{meetup_id}/candidates?q=VER").get_json()["candidates"]
    assert [(c["user"]["login"], c["status"]) for c in candidates] == [("vera", None)]

    response = org.post(
        f"/api/meetups/{meetup_id}/participants", json={"user_id": candidates[0]["user"]["id"]},
    )

    assert response.status_code == 201
    assert response.get_json()["temporary_password"] is None
    with world["app"].app_context():
        participant = db.session.get(MeetupParticipant, (meetup_id, user_id_of(world, "vera")))
        assert participant.status == "approved"


def test_candidates_search_by_cyrillic_name(world, org, meetup_id):
    candidates = org.get(f"/api/meetups/{meetup_id}/candidates?q=иван").get_json()["candidates"]
    assert {c["user"]["login"] for c in candidates} >= {"anna", "boris"}


def test_add_new_account_with_temporary_password(world, org, meetup_id):
    response = org.post(f"/api/meetups/{meetup_id}/participants", json={
        "display_name": "Пётр Новиков", "login": "Petr",
    })

    assert response.status_code == 201
    password = response.get_json()["temporary_password"]
    assert len(password) == 10
    with world["app"].app_context():
        user = db.session.scalar(db.select(User).where(User.login == "petr"))
        assert user.must_change_password
        assert db.session.get(MeetupParticipant, (meetup_id, user.id)).status == "approved"
    login = world["app"].test_client().post(
        "/api/auth/login", json={"login": "petr", "password": password},
    )
    assert login.get_json()["user"]["must_change_password"] is True


def test_new_account_login_must_be_free(org, meetup_id):
    response = org.post(f"/api/meetups/{meetup_id}/participants", json={
        "display_name": "Анна Иванова", "login": "anna",
    })
    assert error(response)["fields"] == {"login": "Логин уже занят"}


def test_banned_member_cannot_be_added(world, org, meetup_id):
    user_id = create_user(world["app"], "banned", MEMBER, world["club_id"], banned=True)
    response = org.post(f"/api/meetups/{meetup_id}/participants", json={"user_id": user_id})
    assert error(response)["code"] == "banned"


# Scrambles for printing

def test_print_scrambles_skip_fmc(org, meetup_id):
    events = org.get(f"/api/meetups/{meetup_id}/scrambles").get_json()["events"]
    assert [e["event_id"] for e in events] == ["333", "222"]
    assert len(events[0]["scrambles"]) == 5


# Permissions

def organizer_requests(meetup_id, user_id):
    base = f"/api/meetups/{meetup_id}"
    return [
        ("get", f"{base}/desk", None),
        ("put", attempt_url(meetup_id, user_id, 1), {"value": 1000, "penalty": "none"}),
        ("delete", attempt_url(meetup_id, user_id, 1), {"version": 1}),
        ("get", f"{base}/candidates", None),
        ("post", f"{base}/participants", {"user_id": user_id}),
        ("put", f"{base}/participants/{user_id}/disqualification", {"reason": "Причина"}),
        ("delete", f"{base}/participants/{user_id}/disqualification", None),
        ("get", f"{base}/finish-summary", None),
        ("post", f"{base}/fmc/1/1/resolve", {"value": None, "penalty": "dnf", "version": 1}),
        ("post", f"{base}/finish", None),
        ("get", f"{base}/scrambles", None),
    ]


def test_only_organizer_has_access(world, clients, meetup_id):
    boris = user_id_of(world, "boris")
    guest = world["app"].test_client()
    for method, url, body in organizer_requests(meetup_id, boris):
        kwargs = {"json": body} if body is not None else {}
        assert getattr(guest, method)(url, **kwargs).status_code == 401, url
        assert getattr(clients["anna"], method)(url, **kwargs).status_code == 403, url

    # Nothing has changed.
    assert results(clients["anna"], meetup_id) == []

