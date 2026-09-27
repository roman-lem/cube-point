"""Organizer access to personal data and the organizer pledge.

An organizer sees only logins, display names, results and meetup participation
of their own club's members: never emails, never other clubs' members.
"""

import pytest

from app.extensions import db
from app.models import ClubMember, ClubRole, OrganizerPledge, User
from app.pledge import PLEDGE_TEXT, PLEDGE_VERSION

from .helpers import MEMBER, ORGANIZER, client_for, create_club, create_user, error
from .test_desk import attempt_url, put
from .test_series import (  # noqa: F401 — fixtures
    clients, meetup_data, meetup_id, org, solve, user_id_of, world,
)


def set_emails(world):
    with world["app"].app_context():
        for user in db.session.scalars(db.select(User)):
            user.email = f"{user.login}@example.com"
        db.session.commit()


def other_club(world):
    """Club B with its organizer "orgb" and member "bella"; returns B's id."""
    club_id = create_club(world["app"])
    create_user(world["app"], "orgb", ORGANIZER, club_id)
    create_user(world["app"], "bella", MEMBER, club_id)
    return club_id


# No emails

def organizer_responses(world, org, clients, meetup_id):
    """Every response an organizer gets while running the club and the meetup."""
    club = world["club_id"]
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000])
    responses = [
        org.get(f"/api/clubs/{club}"),
        org.get(f"/api/clubs/{club}/members"),
        org.get(f"/api/clubs/{club}/members/{anna}"),
        org.get(f"/api/clubs/{club}/meetups"),
        org.get(f"/api/clubs/{club}/records"),
        org.get(f"/api/meetups/{meetup_id}"),
        org.get(f"/api/meetups/{meetup_id}/requests"),
        org.get(f"/api/meetups/{meetup_id}/desk"),
        org.get(f"/api/meetups/{meetup_id}/candidates"),
        org.get(f"/api/meetups/{meetup_id}/finish-summary"),
        org.get(f"/api/meetups/{meetup_id}/events/333/results"),
        org.get(attempt_url(meetup_id, anna, 1) + "/history"),
        org.get(f"/api/users/{anna}"),
        org.get(f"/api/users/{anna}/meetups"),
        org.post(f"/api/clubs/{club}/members", json={"display_name": "Новичок", "login": "newbie"}),
        org.post(
            f"/api/meetups/{meetup_id}/requests/{user_id_of(world, 'pending')}/approve",
        ),
        org.post(f"/api/meetups/{meetup_id}/participants", json={"user_id": anna}),
        put(org, meetup_id, user_id_of(world, "boris"), 1, 1200),
    ]
    for response in responses:
        assert response.status_code < 400, (response.request.path, response.get_json())
    return responses


def test_organizer_never_gets_emails(world, org, clients, meetup_id):
    set_emails(world)
    for response in organizer_responses(world, org, clients, meetup_id):
        body = response.get_data(as_text=True)
        assert '"email"' not in body, response.request.path
        assert "@example.com" not in body, response.request.path


# Other clubs

def test_cannot_add_member_of_another_club(world, org, meetup_id):
    other_club(world)
    bella = user_id_of(world, "bella")

    response = org.post(f"/api/meetups/{meetup_id}/participants", json={"user_id": bella})

    assert response.status_code == 404
    assert "bella" not in response.get_data(as_text=True)
    with world["app"].app_context():
        assert db.session.get(ClubMember, (world["club_id"], bella)) is None


def test_cannot_add_user_without_club(world, org, meetup_id):
    loner = create_user(world["app"], "loner")
    missing = loner + 1000

    responses = [
        org.post(f"/api/meetups/{meetup_id}/participants", json={"user_id": user_id})
        for user_id in (loner, missing)
    ]

    # The same answer: it does not reveal whether the id exists.
    assert [r.status_code for r in responses] == [404, 404]
    assert responses[0].get_json() == responses[1].get_json()


def test_other_club_data_is_closed(world, org, clients, meetup_id):
    """The organizer of club A gets nothing organizer-only from club B."""
    club_b = other_club(world)
    orgb = client_for(world["app"], "orgb")
    bella_client = client_for(world["app"], "bella")
    meetup_b = orgb.post(f"/api/clubs/{club_b}/meetups", json=meetup_data()).get_json()["meetup"]
    bella_client.post(f"/api/join/{meetup_b['join_token']}")
    bella = user_id_of(world, "bella")

    forbidden = [
        org.get(f"/api/clubs/{club_b}/members/{bella}"),
        org.post(f"/api/clubs/{club_b}/members/{bella}/password-reset"),
        org.get(f"/api/meetups/{meetup_b['id']}/requests"),
        org.get(f"/api/meetups/{meetup_b['id']}/desk"),
        org.get(f"/api/meetups/{meetup_b['id']}/candidates"),
        org.get(f"/api/meetups/{meetup_b['id']}/finish-summary"),
        org.post(f"/api/meetups/{meetup_b['id']}/requests/{bella}/approve"),
    ]
    assert [r.status_code for r in forbidden] == [403] * len(forbidden)

    # Public pages of club B: no logins and no join link.
    members = org.get(f"/api/clubs/{club_b}/members").get_json()
    assert all("login" not in m["user"] for m in members["members"])
    assert "filter_counts" not in members
    assert "join_token" not in org.get(f"/api/meetups/{meetup_b['id']}").get_json()["meetup"]


def test_card_does_not_reveal_role_in_another_club(world, org):
    club_b = create_club(world["app"])
    with world["app"].app_context():
        db.session.add(ClubMember(
            club_id=club_b, user_id=user_id_of(world, "anna"), role=ClubRole.ORGANIZER,
        ))
        db.session.commit()
    anna = user_id_of(world, "anna")

    reason = org.get(f"/api/clubs/{world['club_id']}/members/{anna}").get_json()[
        "member"]["restrictions"]["reset_password"]
    response = org.post(f"/api/clubs/{world['club_id']}/members/{anna}/password-reset")

    assert reason == "Пароль этого участника сбрасывает администратор"
    assert response.status_code == 409
    assert error(response)["message"] == reason


# Organizer pledge

@pytest.fixture
def newcomer(world):
    """An organizer of the club without the accepted pledge (appointed before the pledge existed)."""
    create_user(world["app"], "fresh", ORGANIZER, world["club_id"], pledge=False)
    return client_for(world["app"], "fresh")


def accept(client, world, version=PLEDGE_VERSION):
    return client.post(
        f"/api/clubs/{world['club_id']}/organizer-pledge", json={"version": version},
    )


def test_club_page_shows_pledge(world, newcomer, org, clients):
    club = world["club_id"]
    assert newcomer.get(f"/api/clubs/{club}").get_json()["pledge"] == {
        "version": PLEDGE_VERSION, "text": PLEDGE_TEXT,
    }
    assert org.get(f"/api/clubs/{club}").get_json()["pledge"] is None
    assert clients["anna"].get(f"/api/clubs/{club}").get_json()["pledge"] is None


def test_tools_closed_until_pledge(world, newcomer, meetup_id):
    club = world["club_id"]
    anna = user_id_of(world, "anna")
    requests = [
        newcomer.get(f"/api/clubs/{club}/members/{anna}"),
        newcomer.post(f"/api/clubs/{club}/members", json={"display_name": "Новичок", "login": "nb"}),
        newcomer.patch(f"/api/clubs/{club}", json={"name": "X", "city": "Y"}),
        newcomer.get(f"/api/meetups/{meetup_id}/requests"),
        newcomer.get(f"/api/meetups/{meetup_id}/desk"),
        newcomer.post(f"/api/meetups/{meetup_id}/token"),
    ]
    assert [r.status_code for r in requests] == [403] * len(requests)
    assert {error(r)["code"] for r in requests} == {"pledge_required"}

    members = newcomer.get(f"/api/clubs/{club}/members").get_json()
    assert members["can_manage"] is False
    assert all("login" not in m["user"] for m in members["members"])
    meetup = newcomer.get(f"/api/meetups/{meetup_id}").get_json()
    assert "join_token" not in meetup["meetup"]
    assert meetup["pledge"]["version"] == PLEDGE_VERSION


def test_accepting_pledge_opens_tools(world, newcomer, meetup_id):
    assert accept(newcomer, world).status_code == 204
    assert accept(newcomer, world).status_code == 204  # repeated: no second entry

    assert newcomer.get(f"/api/clubs/{world['club_id']}").get_json()["pledge"] is None
    assert newcomer.get(f"/api/meetups/{meetup_id}/desk").status_code == 200
    with world["app"].app_context():
        pledges = db.session.scalars(db.select(OrganizerPledge)).all()
        fresh = [p for p in pledges if p.user_id == user_id_of(world, "fresh")]
        assert len(fresh) == 1
        assert fresh[0].version == PLEDGE_VERSION
        assert fresh[0].club_id == world["club_id"]
        assert fresh[0].accepted_at is not None


def test_outdated_pledge_version_rejected(world, newcomer):
    response = accept(newcomer, world, "2000-01-01")

    assert response.status_code == 409
    assert error(response)["code"] == "pledge_outdated"
    assert newcomer.get(f"/api/clubs/{world['club_id']}").get_json()["pledge"] is not None


def test_only_organizer_accepts_pledge(world, clients):
    response = accept(clients["anna"], world)

    assert response.status_code == 403
    with world["app"].app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(OrganizerPledge)) == 1


def test_pledge_is_per_club(world, newcomer):
    """A pledge in club A does not open club B."""
    club_b = other_club(world)
    with world["app"].app_context():
        db.session.add(ClubMember(
            club_id=club_b, user_id=user_id_of(world, "fresh"), role=ClubRole.ORGANIZER,
        ))
        db.session.commit()
    accept(newcomer, world)

    assert newcomer.get(f"/api/clubs/{club_b}").get_json()["pledge"] is not None
    assert error(newcomer.get(f"/api/clubs/{club_b}/members/{user_id_of(world, 'bella')}"))[
        "code"] == "pledge_required"


def test_appointed_organizer_accepts_pledge(world, org):
    club = world["club_id"]
    anna = user_id_of(world, "anna")
    anna_client = client_for(world["app"], "anna")
    assert org.put(f"/api/clubs/{club}/members/{anna}/organizer").status_code == 200

    assert anna_client.get(f"/api/clubs/{club}").get_json()["pledge"] is not None
    assert error(anna_client.get(f"/api/clubs/{club}/members/{anna}"))["code"] == "pledge_required"


def test_regranted_role_keeps_pledge(world, org):
    """Removing and granting the role again does not ask again while the text is the same."""
    club = world["club_id"]
    anna = user_id_of(world, "anna")
    anna_client = client_for(world["app"], "anna")
    org.put(f"/api/clubs/{club}/members/{anna}/organizer")
    accept(anna_client, world)
    org.delete(f"/api/clubs/{club}/members/{anna}/organizer")
    org.put(f"/api/clubs/{club}/members/{anna}/organizer")

    assert anna_client.get(f"/api/clubs/{club}").get_json()["pledge"] is None


def test_admin_manages_without_pledge(world, newcomer):
    """The administrator manages club members without being an organizer and without a pledge."""
    create_user(world["app"], "root")
    with world["app"].app_context():
        db.session.scalar(db.select(User).where(User.login == "root")).is_admin = True
        db.session.commit()
    admin = client_for(world["app"], "root")
    anna = user_id_of(world, "anna")

    assert admin.get(f"/api/clubs/{world['club_id']}/members/{anna}").status_code == 200
