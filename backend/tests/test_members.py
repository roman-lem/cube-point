"""Club members: list, member card, password reset, organizers, bans."""

import pytest

from app.auth import throttle
from app.extensions import db
from app.models import ClubMember, ClubRole, LoginFailure, User

from .helpers import MEMBER, ORGANIZER, PASSWORD, client_for, create_club, create_user, error
from .test_series import (  # noqa: F401 — fixtures
    clients, meetup_id, org, solve, start, submit, user_id_of, world,
)


def members_url(world, user_id=None, action=None):
    url = f"/api/clubs/{world['club_id']}/members"
    if user_id is not None:
        url += f"/{user_id}"
    if action:
        url += f"/{action}"
    return url


def make_admin(world, login):
    user_id = create_user(world["app"], login)
    with world["app"].app_context():
        db.session.get(User, user_id).is_admin = True
        db.session.commit()
    return client_for(world["app"], login)


def membership(world, login):
    with world["app"].app_context():
        m = db.session.get(ClubMember, (world["club_id"], user_id_of(world, login)))
        db.session.expunge(m)
        return m


def card(client, world, login):
    response = client.get(members_url(world, user_id_of(world, login)))
    assert response.status_code == 200, response.get_json()
    return response.get_json()["member"]


def ban(client, world, login, reason="Грубил участникам"):
    return client.put(members_url(world, user_id_of(world, login), "ban"), json={"reason": reason})


# Permissions

def manager_requests(world):
    anna = user_id_of(world, "anna")
    return [
        ("get", members_url(world, anna), None),
        ("post", members_url(world), {"display_name": "Новый Участник", "login": "newbie"}),
        ("post", members_url(world, anna, "password-reset"), None),
        ("put", members_url(world, anna, "organizer"), None),
        ("delete", members_url(world, anna, "organizer"), None),
        ("put", members_url(world, anna, "ban"), {"reason": "Причина"}),
        ("delete", members_url(world, anna, "ban"), None),
    ]


@pytest.mark.parametrize("who", ["guest", "member", "other_club_organizer"])
def test_only_organizer_manages_members(world, who):
    app = world["app"]
    if who == "guest":
        client, expected = app.test_client(), 401
    elif who == "member":
        client, expected = client_for(app, "boris"), 403
    else:
        other_club = create_club(app)
        create_user(app, "stranger", ORGANIZER, other_club)
        client, expected = client_for(app, "stranger"), 403

    for method, url, body in manager_requests(world):
        response = getattr(client, method)(url, json=body)
        assert response.status_code == expected, url

    anna = membership(world, "anna")
    assert anna.role == ClubRole.MEMBER and anna.banned_at is None
    with app.app_context():
        assert db.session.scalar(db.select(User).where(User.login == "newbie")) is None


def test_admin_manages_members_without_membership(world):
    admin = make_admin(world, "admin")
    assert card(admin, world, "anna")["user"]["login"] == "anna"
    assert admin.put(members_url(world, user_id_of(world, "anna"), "organizer")).status_code == 200
    assert membership(world, "anna").role == ClubRole.ORGANIZER


# List

def test_public_list_hides_banned(world):
    create_user(world["app"], "banned", MEMBER, world["club_id"], banned=True)

    body = world["app"].test_client().get(members_url(world)).get_json()

    assert {m["user"]["id"] for m in body["members"]} == {
        user_id_of(world, login) for login in ("anna", "boris", "org", "pending")
    }
    assert body["can_manage"] is False
    assert "filter_counts" not in body


def test_organizer_list_filters_and_counts(world, org):
    create_user(world["app"], "banned", MEMBER, world["club_id"], banned=True)

    body = org.get(members_url(world) + "?filter=banned").get_json()
    assert [m["user"]["login"] for m in body["members"]] == ["banned"]
    assert body["members"][0]["banned"] is True
    assert body["filter_counts"] == {"all": 5, "organizers": 1, "banned": 1}

    body = org.get(members_url(world) + "?filter=organizers").get_json()
    assert [m["user"]["login"] for m in body["members"]] == ["org"]


def test_search_by_name_and_login(world, org):
    with world["app"].app_context():
        db.session.get(User, user_id_of(world, "anna")).display_name = "Анна Смирнова"
        db.session.commit()

    by_name = org.get(members_url(world) + "?q=смирн").get_json()["members"]
    by_login = org.get(members_url(world) + "?q=BOR").get_json()["members"]

    assert [m["user"]["login"] for m in by_name] == ["anna"]
    assert [m["user"]["login"] for m in by_login] == ["boris"]


def test_meetups_count_and_card_results(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    solve(clients["anna"], meetup_id, [500], event_id="222")

    members = org.get(members_url(world)).get_json()["members"]
    counts = {m["user"]["login"]: m["meetups_count"] for m in members}
    assert counts["anna"] == 1 and counts["boris"] == 0

    anna = card(org, world, "anna")
    assert anna["meetups_count"] == 1
    assert anna["live_meetup"]["id"] == meetup_id
    events = anna["meetups"][0]["events"]
    assert [e["event_id"] for e in events] == ["333", "222"]
    assert events[0] == {
        "event_id": "333", "format": "ao5", "status": "completed",
        "best": 1000, "average": 1200, "place": 1,
        "marks": {"single": ["LR", "PB"], "average": ["LR", "PB"]},
    }


def test_create_member_account(world, org):
    response = org.post(members_url(world), json={"display_name": "Новый Участник", "login": "Newbie"})

    assert response.status_code == 201, response.get_json()
    password = response.get_json()["temporary_password"]
    assert membership(world, "newbie").role == ClubRole.MEMBER
    client = world["app"].test_client()
    login = client.post("/api/auth/login", json={"login": "newbie", "password": password})
    assert login.get_json()["user"]["must_change_password"] is True


def test_create_member_account_while_registration_closed(world, org):
    world["app"].config["REGISTRATION_OPEN"] = False

    response = org.post(members_url(world), json={"display_name": "Новичок", "login": "newbie"})

    assert response.status_code == 201, response.get_json()


def test_create_member_with_taken_login(world, org):
    response = org.post(members_url(world), json={"display_name": "Анна Вторая", "login": "anna"})
    assert response.status_code == 422
    assert error(response)["fields"]["login"] == "Логин уже занят"


# Password reset

def test_password_reset_revokes_sessions(world, org, clients):
    anna = clients["anna"]
    assert anna.get("/api/me/active").status_code == 200

    response = org.post(members_url(world, user_id_of(world, "anna"), "password-reset"))

    assert response.status_code == 200
    password = response.get_json()["temporary_password"]
    # The old session no longer works.
    assert anna.get("/api/me/active").status_code == 401
    # The old password does not work; the temporary one does but requires a change.
    client = world["app"].test_client()
    old = client.post("/api/auth/login", json={"login": "anna", "password": PASSWORD})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"login": "anna", "password": password})
    assert new.get_json()["user"]["must_change_password"] is True
    assert error(client.get("/api/me/active"))["code"] == "password_change_required"


def test_password_reset_clears_login_throttle(world, org):
    with world["app"].app_context():
        for number in range(throttle.LOGIN_LIMIT):
            db.session.add(LoginFailure(login="anna", ip=f"203.0.113.{number}"))
        db.session.commit()
        assert throttle.seconds_until_unblocked("anna", "198.51.100.1") is not None

    org.post(members_url(world, user_id_of(world, "anna"), "password-reset"))

    with world["app"].app_context():
        assert throttle.seconds_until_unblocked("anna", "198.51.100.1") is None


def test_organizer_cannot_reset_organizer_password(world, org):
    create_user(world["app"], "org2", ORGANIZER, world["club_id"])
    url = members_url(world, user_id_of(world, "org2"), "password-reset")

    response = org.post(url)

    assert response.status_code == 409
    assert error(response)["message"] == "Пароль организатора сбрасывает администратор"
    assert card(org, world, "org2")["restrictions"]["reset_password"] is not None


def test_organizer_of_another_club_is_protected(world, org):
    """A member of this club but an organizer of another: only the administrator resets the password."""
    other_club = create_club(world["app"])
    with world["app"].app_context():
        db.session.add(ClubMember(
            club_id=other_club, user_id=user_id_of(world, "anna"), role=ClubRole.ORGANIZER,
        ))
        db.session.commit()

    response = org.post(members_url(world, user_id_of(world, "anna"), "password-reset"))

    assert response.status_code == 409


def test_organizer_cannot_reset_admin_password(world, org):
    with world["app"].app_context():
        db.session.get(User, user_id_of(world, "anna")).is_admin = True
        db.session.commit()

    response = org.post(members_url(world, user_id_of(world, "anna"), "password-reset"))

    assert response.status_code == 409


def test_nobody_resets_own_password(world, org):
    response = org.post(members_url(world, user_id_of(world, "org"), "password-reset"))
    assert response.status_code == 409


def set_email(world, login, address):
    with world["app"].app_context():
        db.session.get(User, user_id_of(world, login)).email = address
        db.session.commit()


def test_organizer_cannot_reset_password_of_member_with_email(world, org):
    """With a confirmed email the member restores the password by themselves."""
    set_email(world, "anna", "anna@example.com")

    response = org.post(members_url(world, user_id_of(world, "anna"), "password-reset"))

    assert response.status_code == 409
    reason = "У участника привязана почта, он может восстановить пароль сам"
    assert error(response)["message"] == reason
    assert card(org, world, "anna")["restrictions"]["reset_password"] == reason
    client_for(world["app"], "anna")  # the password did not change


def test_admin_resets_password_of_member_with_email(world, org):
    set_email(world, "anna", "anna@example.com")
    admin = make_admin(world, "admin")

    response = admin.post(members_url(world, user_id_of(world, "anna"), "password-reset"))

    assert response.status_code == 200
    assert card(admin, world, "anna")["restrictions"]["reset_password"] is None


def test_admin_resets_organizer_password(world, org):
    admin = make_admin(world, "admin")

    response = admin.post(members_url(world, user_id_of(world, "org"), "password-reset"))

    assert response.status_code == 200
    assert org.get(members_url(world)).get_json()["can_manage"] is False  # session revoked


# Organizers

def test_promote_and_demote_organizer(world, org):
    anna = user_id_of(world, "anna")
    admin = make_admin(world, "admin")

    response = org.put(members_url(world, anna, "organizer"))
    assert response.get_json()["member"]["role"] == "organizer"

    response = admin.delete(members_url(world, anna, "organizer"))
    assert response.get_json()["member"]["role"] == "member"
    assert membership(world, "anna").role == ClubRole.MEMBER


def test_organizer_cannot_demote_another_organizer(world, org):
    # Otherwise the next step would be resetting the former organizer's password.
    create_user(world["app"], "org2", ORGANIZER, world["club_id"])

    response = org.delete(members_url(world, user_id_of(world, "org2"), "organizer"))

    assert response.status_code == 409
    assert error(response)["message"] == "Права другого организатора снимает администратор"
    assert membership(world, "org2").role == ClubRole.ORGANIZER
    assert card(org, world, "org2")["restrictions"]["organizer"] == (
        "Права другого организатора снимает администратор"
    )
    # Appointing is still the organizer's: the restriction is only about removing.
    assert card(org, world, "anna")["restrictions"]["organizer"] is None


def test_admin_demotes_any_organizer(world, org):
    create_user(world["app"], "org2", ORGANIZER, world["club_id"])
    admin = make_admin(world, "admin")
    assert card(admin, world, "org2")["restrictions"]["organizer"] is None

    response = admin.delete(members_url(world, user_id_of(world, "org2"), "organizer"))

    assert response.status_code == 200
    assert membership(world, "org2").role == ClubRole.MEMBER


def test_cannot_demote_last_organizer(world, org):
    response = org.delete(members_url(world, user_id_of(world, "org"), "organizer"))

    assert response.status_code == 409
    assert error(response)["message"] == "Нельзя снять последнего организатора"
    assert membership(world, "org").role == ClubRole.ORGANIZER
    assert card(org, world, "org")["restrictions"]["organizer"] == (
        "Нельзя снять последнего организатора"
    )


def test_organizer_can_step_down_if_not_last(world, org):
    create_user(world["app"], "org2", ORGANIZER, world["club_id"])

    response = org.delete(members_url(world, user_id_of(world, "org"), "organizer"))

    assert response.status_code == 200
    assert membership(world, "org").role == ClubRole.MEMBER


def test_banned_cannot_become_organizer(world, org):
    create_user(world["app"], "banned", MEMBER, world["club_id"], banned=True)

    response = org.put(members_url(world, user_id_of(world, "banned"), "organizer"))

    assert response.status_code == 409
    assert membership(world, "banned").role == ClubRole.MEMBER


# Bans

def test_ban_and_unban(world, org):
    response = ban(org, world, "anna", "  Грубил   участникам ")

    assert response.status_code == 200
    ban_info = response.get_json()["member"]["ban"]
    assert ban_info["reason"] == "Грубил участникам"
    assert ban_info["banned_by"]["id"] == user_id_of(world, "org")

    response = org.delete(members_url(world, user_id_of(world, "anna"), "ban"))
    assert response.get_json()["member"]["ban"] is None
    assert membership(world, "anna").banned_at is None


def test_ban_requires_reason(world, org):
    response = ban(org, world, "anna", " ")

    assert response.status_code == 422
    assert error(response)["fields"]["reason"] == "Укажите причину"
    assert membership(world, "anna").banned_at is None


def test_cannot_ban_organizer(world, org):
    create_user(world["app"], "org2", ORGANIZER, world["club_id"])

    response = ban(org, world, "org2")

    assert response.status_code == 409
    assert error(response)["message"] == "Сначала снимите права организатора"
    assert membership(world, "org2").banned_at is None


def test_organizer_cannot_ban_admin(world, org):
    with world["app"].app_context():
        db.session.get(User, user_id_of(world, "anna")).is_admin = True
        db.session.commit()

    response = ban(org, world, "anna")

    assert response.status_code == 409
    assert error(response)["message"] == "Администратора нельзя заблокировать"
    assert membership(world, "anna").banned_at is None
    assert card(org, world, "anna")["restrictions"]["ban"] == "Администратора нельзя заблокировать"


def test_cannot_ban_self(world):
    admin = make_admin(world, "admin")
    with world["app"].app_context():
        db.session.add(ClubMember(club_id=world["club_id"], user_id=user_id_of(world, "admin")))
        db.session.commit()

    response = ban(admin, world, "admin")

    assert response.status_code == 409
    assert error(response)["message"] == "Нельзя заблокировать самого себя"


def test_ban_keeps_results_and_records(world, org, clients, meetup_id):
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    table_before = clients["boris"].get(f"/api/meetups/{meetup_id}/events/333/results").get_json()

    assert ban(org, world, "anna").status_code == 200

    table_after = clients["boris"].get(f"/api/meetups/{meetup_id}/events/333/results").get_json()
    assert table_after == table_before


def test_banned_mid_meetup_stops_submitting(world, org, clients, meetup_id):
    series = solve(clients["anna"], meetup_id, [1000, 1100])

    assert ban(org, world, "anna").status_code == 200

    response = submit(clients["anna"], series, 1200)
    assert response.status_code == 403
    assert error(response)["code"] == "banned"
    assert error(start(clients["anna"], meetup_id, "222"))["code"] == "banned"
    fmc_series = start(clients["anna"], meetup_id, "333fm")
    assert error(fmc_series)["code"] == "banned"
    # Submitted attempts stay; the organizer still enters results for the member.
    anna = user_id_of(world, "anna")
    response = org.put(
        f"/api/meetups/{meetup_id}/events/333/participants/{anna}/attempts/3",
        json={"value": 1200, "penalty": "none", "version": series["version"]},
    )
    assert response.status_code == 200, response.get_json()


def test_banned_mid_fmc_attempt_stops_draft(world, org, clients, meetup_id):
    series = start(clients["anna"], meetup_id, "333fm").get_json()["series"]
    url = f"/api/series/{series['id']}/fmc"
    assert clients["anna"].post(f"{url}/start", json={"attempt_number": 1}).status_code == 200

    ban(org, world, "anna")

    response = clients["anna"].put(f"{url}/draft", json={"attempt_number": 1, "draft": "R U"})
    assert error(response)["code"] == "banned"
