"""Попытки FMC: старт, черновик, заморозка, сдача и дедлайн."""

from datetime import date, timedelta

import pytest

from app.events import FMC_TIME_LIMIT
from app.extensions import db
from app.models import Attempt, AttemptHistory, ClubRecord, FmcAttempt, User

from .helpers import MEMBER, ORGANIZER, client_for, create_club, create_user, error

SCRAMBLES = ["R U F", "L D B", "F2 U2 R2"]
SOLUTION = "F' U' R'"


@pytest.fixture
def world(app, client):
    club_id = create_club(app)
    create_user(app, "org", ORGANIZER, club_id)
    for login in ("anna", "boris"):
        create_user(app, login, MEMBER, club_id)
    return {"app": app, "club_id": club_id}


def create_live_meetup(world, fmc_format):
    org = client_for(world["app"], "org")
    response = org.post(f"/api/clubs/{world['club_id']}/meetups", json={
        "date": (date.today() + timedelta(days=2)).isoformat(),
        "starts_at": "18:00",
        "place": "Антикафе «Куб»",
        "events": [{
            "event_id": "333fm", "format": fmc_format,
            "scrambles": SCRAMBLES[:3 if fmc_format == "mo3" else 1],
        }],
    })
    meetup = response.get_json()["meetup"]
    clients = {}
    for login in ("anna", "boris"):
        clients[login] = client_for(world["app"], login)
        clients[login].post(f"/api/join/{meetup['join_token']}")
        org.post(f"/api/meetups/{meetup['id']}/requests/{user_id_of(world, login)}/approve")
    assert org.post(f"/api/meetups/{meetup['id']}/start").status_code == 200
    return meetup["id"], clients


@pytest.fixture
def bo1(world):
    return create_live_meetup(world, "bo1")


def user_id_of(world, login):
    with world["app"].app_context():
        return db.session.scalar(db.select(User.id).where(User.login == login))


def start_series(client, meetup_id):
    response = client.post(f"/api/meetups/{meetup_id}/events/333fm/series")
    assert response.status_code == 201
    return response.get_json()["series"]


def fmc(client, series, action, method="post", number=None, **body):
    """Запрос к /api/series/<id>/fmc/<action> для текущей попытки серии."""
    body["attempt_number"] = number or series["next_attempt"]["number"]
    return getattr(client, method)(f"/api/series/{series['id']}/fmc/{action}", json=body)


def start_attempt(client, series):
    response = fmc(client, series, "start")
    assert response.status_code == 200, response.get_json()
    return response.get_json()["series"]


def send_result(client, series, value, solution, penalty="none"):
    return fmc(
        client, series, "result",
        value=value, penalty=penalty, version=series["version"], solution=solution,
    )


def expire(world, series, extra=timedelta(seconds=1)):
    """Сдвигает старт текущей попытки назад так, что её час истёк."""
    with world["app"].app_context():
        fmc_attempt = db.session.get(
            FmcAttempt, (series["id"], series["next_attempt"]["number"]),
        )
        fmc_attempt.started_at -= FMC_TIME_LIMIT + extra
        db.session.commit()


def saved_attempt(world, series_id, number=1):
    with world["app"].app_context():
        attempt = db.session.scalar(db.select(Attempt).where(
            Attempt.series_id == series_id, Attempt.attempt_number == number,
        ))
        db.session.expunge(attempt)
        return attempt


# Старт

def test_scramble_is_hidden_until_start(world, bo1):
    meetup_id, clients = bo1
    series = start_series(clients["anna"], meetup_id)

    assert series["next_attempt"] == {"number": 1, "scramble": None, "fmc": None}
    me = clients["anna"].get(f"/api/meetups/{meetup_id}/events/333fm/series/me")
    assert me.get_json()["series"]["next_attempt"]["scramble"] is None


def test_start_gives_scramble_and_deadline(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))

    attempt = series["next_attempt"]
    assert attempt["scramble"] == SCRAMBLES[0]
    assert attempt["fmc"]["draft"] == ""
    assert attempt["fmc"]["frozen_solution"] is None
    assert attempt["fmc"]["deadline"] > attempt["fmc"]["started_at"]


def test_repeated_start_keeps_first_start(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    again = start_attempt(clients["anna"], series)

    assert again["next_attempt"]["fmc"]["started_at"] == series["next_attempt"]["fmc"]["started_at"]


def test_cannot_start_someone_elses_attempt(world, bo1):
    meetup_id, clients = bo1
    series = start_series(clients["anna"], meetup_id)

    assert fmc(clients["boris"], series, "start").status_code == 403


def test_cannot_skip_attempt(world):
    meetup_id, clients = create_live_meetup(world, "mo3")
    series = start_series(clients["anna"], meetup_id)

    response = fmc(clients["anna"], series, "start", number=2)
    assert response.status_code == 409
    assert error(response)["code"] == "wrong_attempt_number"


def test_draft_and_freeze_need_started_attempt(world, bo1):
    meetup_id, clients = bo1
    series = start_series(clients["anna"], meetup_id)

    for action in ("draft", "freeze"):
        method = "put" if action == "draft" else "post"
        response = fmc(clients["anna"], series, action, method, solution=SOLUTION)
        assert error(response)["code"] == "not_started"


# Черновик

def test_draft_is_saved(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))

    response = fmc(clients["anna"], series, "draft", "put", solution="  F'  U' Rw2 x ")
    assert response.status_code == 200
    me = clients["anna"].get(f"/api/meetups/{meetup_id}/events/333fm/series/me")
    assert me.get_json()["series"]["next_attempt"]["fmc"]["draft"] == "F' U' Rw2 x"


@pytest.mark.parametrize("solution", ["R M", "R3", "r U", "Rw'2", "R" * 1001])
def test_invalid_solution_is_rejected(world, bo1, solution):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))

    response = fmc(clients["anna"], series, "draft", "put", solution=solution)
    assert response.status_code == 422


def test_draft_after_deadline_is_rejected(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    fmc(clients["anna"], series, "draft", "put", solution="F'")
    expire(world, series)

    response = fmc(clients["anna"], series, "draft", "put", solution=SOLUTION)
    assert error(response)["code"] == "time_over"
    me = clients["anna"].get(f"/api/meetups/{meetup_id}/events/333fm/series/me")
    assert me.get_json()["series"]["next_attempt"]["fmc"]["draft"] == "F'"


# Заморозка

def test_freeze_fixes_solution_and_time(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))

    frozen = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]
    state = frozen["next_attempt"]["fmc"]
    assert state["frozen_solution"] == SOLUTION
    assert state["frozen_at"] is not None

    # Повторная заморозка и черновик не меняют замороженный текст.
    again = fmc(clients["anna"], series, "freeze", solution="R").get_json()["series"]
    assert again["next_attempt"]["fmc"]["frozen_solution"] == SOLUTION
    assert again["next_attempt"]["fmc"]["frozen_at"] == state["frozen_at"]
    assert error(fmc(clients["anna"], series, "draft", "put", solution="R"))["code"] == "frozen"


def test_unfreeze_allows_new_submission_time(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    first = fmc(clients["anna"], series, "freeze", solution="F'").get_json()["series"]

    response = fmc(clients["anna"], series, "freeze", "delete")
    assert response.status_code == 200
    state = response.get_json()["series"]["next_attempt"]["fmc"]
    assert state["frozen_solution"] is None and state["frozen_at"] is None
    # Черновик остаётся тем, что было заморожено.
    assert state["draft"] == "F'"

    second = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]
    assert second["next_attempt"]["fmc"]["frozen_solution"] == SOLUTION
    assert (
        second["next_attempt"]["fmc"]["frozen_at"] >= first["next_attempt"]["fmc"]["frozen_at"]
    )


def test_unfreeze_after_deadline_is_rejected(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    fmc(clients["anna"], series, "freeze", solution=SOLUTION)
    expire(world, series)

    assert error(fmc(clients["anna"], series, "freeze", "delete"))["code"] == "time_over"


def test_freeze_after_deadline_saves_dnf_with_solution(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    expire(world, series)

    response = fmc(clients["anna"], series, "freeze", solution=SOLUTION)
    assert response.status_code == 200
    saved = response.get_json()["series"]
    assert saved["status"] == "completed"
    assert saved["attempts"] == [
        {"number": 1, "value": None, "penalty": "dnf", "solution": SOLUTION},
    ]


# Сдача

def test_result_is_saved_with_frozen_solution(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    frozen = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]

    response = send_result(clients["anna"], frozen, 3, SOLUTION)
    assert response.status_code == 201
    saved = response.get_json()["series"]
    assert saved["status"] == "completed"
    assert saved["best"] == 3
    assert saved["attempts"] == [
        {"number": 1, "value": 3, "penalty": "none", "solution": SOLUTION},
    ]
    attempt = saved_attempt(world, series["id"])
    assert attempt.submitted_at.isoformat() + "Z" == frozen["next_attempt"]["fmc"]["frozen_at"]
    with world["app"].app_context():
        [entry] = db.session.scalars(
            db.select(AttemptHistory).where(AttemptHistory.attempt_id == attempt.id)
        ).all()
        assert (entry.value, entry.solution) == (3, SOLUTION)
        assert entry.changed_by == user_id_of(world, "anna")


def test_result_goes_through_records(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    frozen = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]
    send_result(clients["anna"], frozen, 3, SOLUTION)

    with world["app"].app_context():
        record = db.session.scalar(db.select(ClubRecord).where(ClubRecord.event_id == "333fm"))
        assert (record.user_id, record.value) == (user_id_of(world, "anna"), 3)
    rows = clients["boris"].get(f"/api/meetups/{meetup_id}/events/333fm/results").get_json()["rows"]
    assert rows[0]["place"] == 1 and rows[0]["best"] == 3


def test_result_without_freeze_is_rejected(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    fmc(clients["anna"], series, "draft", "put", solution=SOLUTION)

    response = send_result(clients["anna"], series, 3, SOLUTION)
    assert error(response)["code"] == "not_frozen"


def test_result_for_other_text_is_rejected(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    frozen = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]

    response = send_result(clients["anna"], frozen, 1, "F'")
    assert error(response)["code"] == "solution_changed"
    assert response.get_json()["error"]["series"]["next_attempt"]["fmc"]["frozen_solution"] == SOLUTION


@pytest.mark.parametrize("value, penalty", [
    (0, "none"), (81, "none"), (None, "none"), (30, "plus2"), (30, "dns"), (2.5, "none"),
])
def test_invalid_result(world, bo1, value, penalty):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    frozen = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]

    assert send_result(clients["anna"], frozen, value, SOLUTION, penalty).status_code == 422


def test_dnf_result_keeps_solution(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    frozen = fmc(clients["anna"], series, "freeze", solution="R U").get_json()["series"]

    response = send_result(clients["anna"], frozen, None, "R U", penalty="dnf")
    assert response.status_code == 201
    assert saved_attempt(world, series["id"]).solution == "R U"


def test_draft_becomes_result_after_deadline(world, bo1):
    meetup_id, clients = bo1
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    fmc(clients["anna"], series, "draft", "put", solution=SOLUTION)
    expire(world, series, extra=timedelta(minutes=5))

    response = send_result(clients["anna"], series, 3, SOLUTION)
    assert response.status_code == 201
    attempt = saved_attempt(world, series["id"])
    assert attempt.solution == SOLUTION
    with world["app"].app_context():
        fmc_attempt = db.session.get(FmcAttempt, (series["id"], 1))
        # Время сдачи — дедлайн, а не момент проверки.
        assert attempt.submitted_at == fmc_attempt.started_at + FMC_TIME_LIMIT


def test_mo3_attempts_have_own_start(world):
    meetup_id, clients = create_live_meetup(world, "mo3")
    series = start_attempt(clients["anna"], start_series(clients["anna"], meetup_id))
    frozen = fmc(clients["anna"], series, "freeze", solution=SOLUTION).get_json()["series"]
    series = send_result(clients["anna"], frozen, 3, SOLUTION).get_json()["series"]

    # Вторая попытка не начата: скрамбла нет, пока её не стартовали.
    assert series["next_attempt"] == {"number": 2, "scramble": None, "fmc": None}
    series = start_attempt(clients["anna"], series)
    assert series["next_attempt"]["scramble"] == SCRAMBLES[1]
    with world["app"].app_context():
        first, second = db.session.scalars(
            db.select(FmcAttempt).order_by(FmcAttempt.attempt_number)
        ).all()
        assert second.started_at >= first.frozen_at


def test_fmc_endpoints_reject_timed_series(world, app):
    club_id = world["club_id"]
    org = client_for(app, "org")
    meetup = org.post(f"/api/clubs/{club_id}/meetups", json={
        "date": (date.today() + timedelta(days=2)).isoformat(),
        "starts_at": "18:00",
        "place": "Антикафе «Куб»",
        "events": [{"event_id": "222", "format": "bo1", "scrambles": ["R U"]}],
    }).get_json()["meetup"]
    anna = client_for(app, "anna")
    anna.post(f"/api/join/{meetup['join_token']}")
    org.post(f"/api/meetups/{meetup['id']}/requests/{user_id_of(world, 'anna')}/approve")
    org.post(f"/api/meetups/{meetup['id']}/start")
    series = anna.post(f"/api/meetups/{meetup['id']}/events/222/series").get_json()["series"]

    assert error(fmc(anna, series, "start"))["code"] == "not_fmc"
