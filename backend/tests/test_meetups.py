"""Meetups, joining by link and participation requests: access rights and domain rules."""

from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import ClubMember, ClubRole, Meetup, MeetupStatus

from .helpers import MEMBER, ORGANIZER, client_for, create_club, create_user, error

TOMORROW = (date.today() + timedelta(days=2)).isoformat()


def meetup_data(**overrides):
    data = {
        "date": TOMORROW,
        "starts_at": "18:00",
        "ends_at": "21:00",
        "place": "Антикафе «Куб»",
        "address": "",
        "events": [
            {"event_id": "333", "format": "ao5", "scrambles": ["R U R' U'"] * 5},
            {"event_id": "333fm", "format": "bo1", "scrambles": ["R' U' F D2 R' U' F"]},
        ],
    }
    data.update(overrides)
    return data


@pytest.fixture
def world(app, client):
    """A club, its organizer, a member, a banned user and an outsider."""
    club_id = create_club(app)
    create_user(app, "org", ORGANIZER, club_id)
    member_id = create_user(app, "member", MEMBER, club_id)
    create_user(app, "banned", MEMBER, club_id, banned=True)
    stranger_id = create_user(app, "stranger")
    return {"app": app, "club_id": club_id, "member_id": member_id, "stranger_id": stranger_id}


@pytest.fixture
def org(world):
    return client_for(world["app"], "org")


@pytest.fixture
def meetup(world, org):
    response = org.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())
    assert response.status_code == 201
    return response.get_json()["meetup"]


def join(client, token):
    return client.post(f"/api/join/{token}")


# Creating a meetup

def test_organizer_creates_meetup(world, org):
    response = org.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())

    assert response.status_code == 201
    meetup = response.get_json()["meetup"]
    assert meetup["status"] == "planned"
    assert meetup["date"] == TOMORROW
    # Tyumen is UTC+5: 18:00 by the club's clock is 13:00 UTC.
    assert meetup["starts_at"] == f"{TOMORROW}T13:00:00Z"
    assert meetup["ends_at"] == f"{TOMORROW}T16:00:00Z"
    assert meetup["address"] is None
    assert [(e["event_id"], e["format"]) for e in meetup["events"]] == [
        ("333", "ao5"), ("333fm", "bo1"),
    ]
    assert meetup["join_token"]


@pytest.mark.parametrize("login", ["member", "stranger"])
def test_not_organizer_cannot_create_meetup(world, login):
    client = client_for(world["app"], login)

    response = client.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())

    assert response.status_code == 403


def test_guest_cannot_create_meetup(world):
    client = world["app"].test_client()

    response = client.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())

    assert response.status_code == 401


@pytest.mark.parametrize("events, field", [
    ([], "events"),
    ([{"event_id": "333mbf", "format": "bo1", "scrambles": ["R"]}], "events.0.event_id"),
    ([{"event_id": "333", "format": "ao7", "scrambles": ["R"] * 5}], "events.0.format"),
    ([{"event_id": "333", "format": "ao5", "scrambles": ["R"] * 4}], "events.0.scrambles"),
    ([{"event_id": "333", "format": "mo3", "scrambles": ["R"] * 5}], "events.0.scrambles"),
    ([{"event_id": "333", "format": "bo1", "scrambles": ["  "]}], "events.0.scrambles"),
    ([{"event_id": "333", "format": "bo1", "scrambles": ["R " * 501]}], "events.0.scrambles"),
    (
        [{"event_id": "222", "format": "bo1", "scrambles": ["R"]}] * 2,
        "events.1.event_id",
    ),
])
def test_create_meetup_checks_events(world, org, events, field):
    response = org.post(
        f"/api/clubs/{world['club_id']}/meetups", json=meetup_data(events=events),
    )

    assert response.status_code == 422
    assert list(error(response)["fields"]) == [field]


def test_meetup_events_are_in_wca_order(world, org):
    # A 7x7 scramble can be about 500 characters long.
    long_scramble = " ".join(["3Rw2"] * 100)
    events = [
        {"event_id": "555bf", "format": "bo3", "scrambles": ["Rw"] * 3},
        {"event_id": "777", "format": "mo3", "scrambles": [long_scramble] * 3},
        {"event_id": "minx", "format": "bo1", "scrambles": ["R++ D-- U R-- D++ U'"]},
        {"event_id": "333", "format": "bo1", "scrambles": ["R"]},
    ]
    response = org.post(
        f"/api/clubs/{world['club_id']}/meetups", json=meetup_data(events=events),
    )
    assert response.status_code == 201
    created = response.get_json()["meetup"]["events"]
    assert [e["event_id"] for e in created] == ["333", "777", "minx", "555bf"]

    meetup_id = response.get_json()["meetup"]["id"]
    page = org.get(f"/api/meetups/{meetup_id}").get_json()["meetup"]
    assert [e["event_id"] for e in page["events"]] == ["333", "777", "minx", "555bf"]


@pytest.mark.parametrize("overrides, field", [
    ({"date": "2020-01-01"}, "date"),
    ({"date": "завтра"}, "date"),
    ({"starts_at": ""}, "starts_at"),
    ({"starts_at": "25:00"}, "starts_at"),
    ({"ends_at": "17:00"}, "ends_at"),
    ({"place": " "}, "place"),
])
def test_create_meetup_checks_fields(world, org, overrides, field):
    response = org.post(
        f"/api/clubs/{world['club_id']}/meetups", json=meetup_data(**overrides),
    )

    assert response.status_code == 422
    assert list(error(response)["fields"]) == [field]


def test_organizer_of_other_club_cannot_create_meetup(world):
    app = world["app"]
    other_club_id = create_club(app)
    create_user(app, "other_org", ORGANIZER, other_club_id)
    client = client_for(app, "other_org")

    response = client.post(f"/api/clubs/{world['club_id']}/meetups", json=meetup_data())

    assert response.status_code == 403


# Meetup page and meetup list

def test_meetup_page_is_public_but_token_is_for_organizer(world, meetup):
    app = world["app"]

    as_guest = app.test_client().get(f"/api/meetups/{meetup['id']}").get_json()
    as_member = client_for(app, "member").get(f"/api/meetups/{meetup['id']}").get_json()

    assert as_guest["my_role"] is None
    assert as_guest["my_request"] is None
    assert "join_token" not in as_guest["meetup"]
    assert as_member["my_role"] == "member"
    assert "join_token" not in as_member["meetup"]


def test_club_meetups_list(world, meetup):
    response = world["app"].test_client().get(f"/api/clubs/{world['club_id']}/meetups")

    [item] = response.get_json()["meetups"]
    assert item["id"] == meetup["id"]
    assert item["events"] == ["333", "333fm"]
    assert item["participants_count"] == 0


# Starting

def test_organizer_starts_meetup(org, meetup):
    response = org.post(f"/api/meetups/{meetup['id']}/start")

    assert response.status_code == 200
    assert response.get_json()["meetup"]["status"] == "live"
    assert org.post(f"/api/meetups/{meetup['id']}/start").status_code == 409


def test_member_cannot_start_meetup(world, meetup):
    client = client_for(world["app"], "member")

    assert client.post(f"/api/meetups/{meetup['id']}/start").status_code == 403


# Joining by link

def test_join_creates_pending_request(world, meetup):
    client = client_for(world["app"], "stranger")

    response = join(client, meetup["join_token"])

    assert response.status_code == 201
    assert response.get_json() == {"meetup_id": meetup["id"], "status": "pending"}
    page = client.get(f"/api/meetups/{meetup['id']}").get_json()
    assert page["my_request"] == {"status": "pending"}
    # Following the link again does not create a second request.
    assert join(client, meetup["join_token"]).status_code == 200


def test_join_preview_is_public(world, meetup):
    response = world["app"].test_client().get(f"/api/join/{meetup['join_token']}")

    assert response.status_code == 200
    assert response.get_json()["meetup"]["club"]["name"] == "Tyumen | Speedcubing"


def test_guest_cannot_join(world, meetup):
    response = join(world["app"].test_client(), meetup["join_token"])

    assert response.status_code == 401


def test_banned_cannot_join(world, meetup):
    client = client_for(world["app"], "banned")

    response = join(client, meetup["join_token"])

    assert response.status_code == 403
    assert error(response)["code"] == "banned"


def test_organizer_is_approved_at_once(org, meetup):
    response = join(org, meetup["join_token"])

    assert response.get_json()["status"] == "approved"


def test_unknown_token(world):
    response = join(client_for(world["app"], "stranger"), "no-such-token")

    assert response.status_code == 404
    assert error(response)["code"] == "invalid_link"


def test_old_token_stops_working_after_reissue(world, org, meetup):
    stranger = client_for(world["app"], "stranger")
    join(stranger, meetup["join_token"])
    org.post(f"/api/meetups/{meetup['id']}/requests/{world['stranger_id']}/approve")

    response = org.post(f"/api/meetups/{meetup['id']}/token")

    new_token = response.get_json()["join_token"]
    assert new_token != meetup["join_token"]
    member = client_for(world["app"], "member")
    assert join(member, meetup["join_token"]).status_code == 404
    assert world["app"].test_client().get(f"/api/join/{meetup['join_token']}").status_code == 404
    assert join(member, new_token).status_code == 201
    # An approved participant stays approved.
    page = stranger.get(f"/api/meetups/{meetup['id']}").get_json()
    assert page["my_request"] == {"status": "approved"}


def test_member_cannot_reissue_token(world, meetup):
    client = client_for(world["app"], "member")

    assert client.post(f"/api/meetups/{meetup['id']}/token").status_code == 403


def test_token_does_not_work_after_meetup_finished(world, meetup):
    app = world["app"]
    with app.app_context():
        db.session.get(Meetup, meetup["id"]).status = MeetupStatus.FINISHED
        db.session.commit()

    response = join(client_for(app, "stranger"), meetup["join_token"])

    assert response.status_code == 404


# Requests

def test_first_approval_adds_to_club(world, org, meetup):
    app = world["app"]
    join(client_for(app, "stranger"), meetup["join_token"])

    response = org.post(f"/api/meetups/{meetup['id']}/requests/{world['stranger_id']}/approve")

    assert response.status_code == 200
    assert response.get_json()["request"]["status"] == "approved"
    with app.app_context():
        membership = db.session.get(ClubMember, (world["club_id"], world["stranger_id"]))
        assert membership.role == ClubRole.MEMBER


def test_member_cannot_see_or_approve_requests(world, meetup):
    app = world["app"]
    join(client_for(app, "stranger"), meetup["join_token"])
    member = client_for(app, "member")
    base = f"/api/meetups/{meetup['id']}/requests"

    assert member.get(base).status_code == 403
    assert member.post(f"{base}/{world['stranger_id']}/approve").status_code == 403
    assert member.post(f"{base}/{world['stranger_id']}/reject").status_code == 403
    assert member.post(f"{base}/approve-all").status_code == 403
    assert client_for(app, "stranger").post(f"{base}/approve-all").status_code == 403


def test_reject_request(world, org, meetup):
    stranger = client_for(world["app"], "stranger")
    join(stranger, meetup["join_token"])
    url = f"/api/meetups/{meetup['id']}/requests/{world['stranger_id']}"

    assert org.post(f"{url}/reject").get_json()["request"]["status"] == "rejected"
    assert org.post(f"{url}/reject").status_code == 409
    # Following the link does not bring the request back to pending.
    assert join(stranger, meetup["join_token"]).get_json()["status"] == "rejected"
    # The organizer can correct a mistake.
    assert org.post(f"{url}/approve").get_json()["request"]["status"] == "approved"


def test_approve_all_skips_banned(world, org, meetup):
    app = world["app"]
    join(client_for(app, "stranger"), meetup["join_token"])
    join(client_for(app, "member"), meetup["join_token"])
    # Banned after the request was made.
    with app.app_context():
        membership = db.session.get(ClubMember, (world["club_id"], world["member_id"]))
        membership.banned_at = membership.joined_at
        db.session.commit()

    response = org.post(f"/api/meetups/{meetup['id']}/requests/approve-all")

    assert response.get_json() == {"approved": 1}
    requests = org.get(f"/api/meetups/{meetup['id']}/requests").get_json()["requests"]
    # Pending ones first.
    assert [(r["user"]["login"], r["status"]) for r in requests] == [
        ("member", "pending"), ("stranger", "approved"),
    ]
