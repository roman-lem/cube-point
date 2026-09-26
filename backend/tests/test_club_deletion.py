"""Club deletion by the administrator: everything of the club goes, users stay."""

import pytest

from app.extensions import db
from app.models import (
    Attempt, AttemptHistory, Club, ClubLink, ClubMember, ClubRecord, Disqualification,
    FmcAttempt, LinkType, Meetup, MeetupEvent, MeetupParticipant, MeetupStatus, Scramble,
    Series, User,
)

from .helpers import client_for, create_user, error
from .test_profiles import disqualify, other_club, personal_records
from .test_series import (  # noqa: F401 — fixtures
    clients, create_live_meetup, meetup_data, org, solve, user_id_of, world,
)

CLUB_NAME = "Tyumen | Speedcubing"
# Everything that belongs to a club, with the column that leads to it.
CLUB_TABLES = {
    Meetup: Meetup.club_id,
    MeetupEvent: Meetup.club_id,
    Scramble: Meetup.club_id,
    MeetupParticipant: Meetup.club_id,
    Series: Meetup.club_id,
    Attempt: Meetup.club_id,
    AttemptHistory: Meetup.club_id,
    FmcAttempt: Meetup.club_id,
    Disqualification: Meetup.club_id,
    ClubRecord: ClubRecord.club_id,
    ClubLink: ClubLink.club_id,
    ClubMember: ClubMember.club_id,
}


@pytest.fixture
def admin(world):
    create_user(world["app"], "admin")
    with world["app"].app_context():
        db.session.scalar(db.select(User).where(User.login == "admin")).is_admin = True
        db.session.commit()
    return client_for(world["app"], "admin")


def count_rows(app, club_id):
    """{table: number of rows of the club}."""
    joins = {
        MeetupEvent: [Meetup],
        Scramble: [MeetupEvent, Meetup],
        MeetupParticipant: [Meetup],
        Series: [MeetupEvent, Meetup],
        Attempt: [Series, MeetupEvent, Meetup],
        AttemptHistory: [Attempt, Series, MeetupEvent, Meetup],
        FmcAttempt: [Series, MeetupEvent, Meetup],
        Disqualification: [Meetup],
    }
    result = {}
    with app.app_context():
        for model, column in CLUB_TABLES.items():
            query = db.select(db.func.count()).select_from(model)
            for parent in joins.get(model, []):
                query = query.join(parent)
            result[model.__tablename__] = db.session.scalar(query.where(column == club_id))
    return result


def finish(app, meetup_id):
    # Directly: the finish endpoint wants the FMC attempt resolved first.
    with app.app_context():
        db.session.get(Meetup, meetup_id).status = MeetupStatus.FINISHED
        db.session.commit()


def delete_club(client, club_id, name=CLUB_NAME):
    return client.delete(f"/api/admin/clubs/{club_id}", json={"name": name})


@pytest.fixture
def full_club(world, org, clients):
    """The club with data in every table; its meetup is finished."""
    app, club_id = world["app"], world["club_id"]
    meetup_id = create_live_meetup(world, org, clients)
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    solve(clients["boris"], meetup_id, [900])
    fmc = solve(clients["boris"], meetup_id, [], event_id="333fm")
    response = clients["boris"].post(
        f"/api/series/{fmc['id']}/fmc/start", json={"attempt_number": 1},
    )
    assert response.status_code == 200, response.get_json()
    disqualify(org, meetup_id, user_id_of(world, "boris"))
    # A planned meetup as well.
    assert org.post(f"/api/clubs/{club_id}/meetups", json=meetup_data(9)).status_code == 201
    org.put(
        f"/api/clubs/{club_id}/members/{user_id_of(world, 'pending')}/ban",
        json={"reason": "Грубил"},
    )
    with app.app_context():
        db.session.add(ClubLink(club_id=club_id, type=LinkType.VK, url="https://vk.com/cube"))
        db.session.commit()
    finish(app, meetup_id)
    return meetup_id


def test_club_details_show_what_will_be_deleted(world, admin, full_club):
    club = admin.get(f"/api/admin/clubs/{world['club_id']}").get_json()["club"]

    # 2 meetups, 4 members (banned too), 5 + 1 attempts.
    assert club["deletion"] == {"meetups": 2, "members": 4, "results": 6}
    assert club["delete_restriction"] is None


def test_deletes_club_with_everything_and_keeps_users(world, admin, full_club):
    app, club_id = world["app"], world["club_id"]
    before = count_rows(app, club_id)
    assert all(before.values()), before
    with app.app_context():
        users_before = db.session.scalar(db.select(db.func.count()).select_from(User))

    response = delete_club(admin, club_id)

    assert response.status_code == 204
    assert set(count_rows(app, club_id).values()) == {0}
    with app.app_context():
        assert db.session.get(Club, club_id) is None
        assert db.session.scalar(db.select(db.func.count()).select_from(User)) == users_before
    # Users can still log in, the organizer too.
    for login in ("org", "anna", "boris", "pending"):
        client_for(app, login)


def test_other_club_is_untouched(world, admin, clients, full_club):
    other, other_meetup = other_club(world, clients)
    solve(clients["anna"], other_meetup, [800])
    before = count_rows(world["app"], other["club_id"])

    delete_club(admin, world["club_id"])

    assert count_rows(world["app"], other["club_id"]) == before


def test_live_meetup_forbids_deletion(world, admin, org, clients):
    meetup_id = create_live_meetup(world, org, clients)
    solve(clients["anna"], meetup_id, [1000])

    club = admin.get(f"/api/admin/clubs/{world['club_id']}").get_json()["club"]
    response = delete_club(admin, world["club_id"])

    assert club["delete_restriction"] == "Идёт встреча — удалить клуб можно после её завершения"
    assert response.status_code == 409
    assert error(response)["code"] == "meetup_live"
    assert count_rows(world["app"], world["club_id"])["attempts"] == 1


@pytest.mark.parametrize("name", ["", "tyumen | speedcubing", "Tyumen"])
def test_name_must_match(world, admin, name):
    response = delete_club(admin, world["club_id"], name)

    assert response.status_code == 422
    assert error(response)["fields"] == {"name": "Название не совпадает"}
    with world["app"].app_context():
        assert db.session.get(Club, world["club_id"]) is not None


def test_name_edges_are_trimmed(world, admin):
    assert delete_club(admin, world["club_id"], f"  {CLUB_NAME} ").status_code == 204


@pytest.mark.parametrize("login", [None, "org", "anna"])
def test_only_admin_deletes(world, login):
    client = client_for(world["app"], login) if login else world["app"].test_client()

    response = delete_club(client, world["club_id"])

    assert response.status_code == (401 if login is None else 403)
    with world["app"].app_context():
        assert db.session.get(Club, world["club_id"]) is not None


def test_unknown_club(world, admin):
    assert delete_club(admin, 999).status_code == 404


def test_personal_records_are_recalculated(world, admin, org, clients):
    anna = user_id_of(world, "anna")
    meetup_id = create_live_meetup(world, org, clients)
    solve(clients["anna"], meetup_id, [900])
    solve(clients["anna"], meetup_id, [500], event_id="222")
    finish(world["app"], meetup_id)
    other, other_meetup = other_club(world, clients)
    solve(clients["anna"], other_meetup, [1000])
    assert personal_records(admin, anna)["333"]["single"]["value"] == 900

    delete_club(admin, world["club_id"])

    records = personal_records(admin, anna)
    assert records["333"]["single"]["value"] == 1000
    assert records["333"]["single"]["meetup"]["club"]["id"] == other["club_id"]
    # The event was only in the deleted club.
    assert "222" not in records


def home_club(client):
    return client.get("/api/auth/home-club").get_json()["club_id"]


def test_home_club_after_deletion(world, admin, clients):
    other, other_meetup = other_club(world, clients)
    # anna stays in the other club (joined at its meetup), boris has only the deleted one.
    with world["app"].app_context():
        db.session.execute(db.delete(ClubMember).where(
            ClubMember.club_id == other["club_id"],
            ClubMember.user_id == user_id_of(world, "boris"),
        ))
        db.session.commit()
    assert home_club(clients["anna"]) == other["club_id"]

    delete_club(admin, world["club_id"])

    assert home_club(clients["anna"]) == other["club_id"]
    assert home_club(clients["boris"]) is None
    assert home_club(client_for(world["app"], "org")) is None
