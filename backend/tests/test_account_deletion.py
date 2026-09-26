"""Удаление аккаунта: персональные данные уничтожаются, результаты и рекорды остаются."""

from app.accounts import DELETED_REASON
from app.consents import CONSENT_VERSIONS
from app.extensions import db
from app.models import (
    DELETED_USER_NAME, ClubMember, ConsentType, Disqualification, LoginFailure, Series, User,
    UserConsent,
)

from .helpers import ORGANIZER, PASSWORD, client_for, create_user, error
from .test_profiles import club_records, disqualify, members, personal_records, profile
from .test_series import (  # noqa: F401 — фикстуры
    clients, meetup_id, org, records, results, solve, user_id_of, world,
)


def delete_account(client, password=PASSWORD, keep_name=False):
    return client.post(
        "/api/auth/delete-account", json={"password": password, "keep_name": keep_name},
    )


def me(client):
    return client.get("/api/auth/me").get_json()["user"]


def get_user(world, user_id):
    with world["app"].app_context():
        user = db.session.get(User, user_id)
        db.session.expunge(user)
        return user


def test_wrong_or_missing_password_keeps_account(world, clients):
    anna = user_id_of(world, "anna")

    wrong = delete_account(clients["anna"], "wrong-password")
    missing = delete_account(clients["anna"], "")

    assert wrong.status_code == 422
    assert error(wrong)["fields"] == {"password": "Неверный пароль"}
    assert error(missing)["fields"] == {"password": "Введите пароль"}
    assert get_user(world, anna).login == "anna"
    assert me(clients["anna"])["id"] == anna


def test_deletion_destroys_personal_data(world, clients):
    anna = user_id_of(world, "anna")
    with world["app"].app_context():
        db.session.get(User, anna).email = "anna@example.com"
        db.session.commit()
    world["app"].test_client().post("/api/auth/login", json={"login": "anna", "password": "x"})

    response = delete_account(clients["anna"])

    assert response.status_code == 204
    user = get_user(world, anna)
    assert user.login is None
    assert user.email is None
    assert user.password_hash is None
    assert user.display_name == DELETED_USER_NAME
    assert user.deleted_at is not None
    with world["app"].app_context():
        assert db.session.scalars(db.select(UserConsent).where(UserConsent.user_id == anna)).all() == []
        assert db.session.scalars(db.select(ClubMember).where(ClubMember.user_id == anna)).all() == []
        assert db.session.scalars(db.select(LoginFailure).where(LoginFailure.login == "anna")).all() == []


def test_deletion_ends_all_sessions_and_frees_login(world, clients):
    other_device = world["app"].test_client()
    other_device.post("/api/auth/login", json={"login": "anna", "password": PASSWORD, "remember": True})

    delete_account(clients["anna"])

    assert me(clients["anna"]) is None
    assert me(other_device) is None
    login = world["app"].test_client().post(
        "/api/auth/login", json={"login": "anna", "password": PASSWORD},
    )
    assert login.status_code == 401
    # Логин освободился, его может занять новый человек.
    create_user(world["app"], "anna")


def test_results_and_records_stay_with_deleted_name(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    guest = world["app"].test_client()

    delete_account(clients["anna"])

    with world["app"].app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Series)
                                 .where(Series.user_id == anna)) == 1
    assert records(world)["single"] == (anna, 1000)
    row = results(guest, meetup_id)[0]
    assert row["user"] == {"id": anna, "display_name": DELETED_USER_NAME, "has_profile": True}
    assert club_records(guest, world)["333"]["single"]["user"]["display_name"] == DELETED_USER_NAME
    # Публичный профиль остаётся, но без клубов: человек вышел из них.
    assert profile(guest, anna)["user"]["display_name"] == DELETED_USER_NAME
    assert profile(guest, anna)["clubs"] == []
    assert personal_records(guest, anna)["333"]["single"]["value"] == 1000
    assert anna not in [m["user"]["id"] for m in members(guest, world)]


def test_ban_and_disqualification_reasons_are_removed(world, org, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    disqualify(org, meetup_id, anna)
    org.put(f"/api/clubs/{world['club_id']}/members/{anna}/ban", json={"reason": "Грубил"})

    delete_account(clients["anna"])

    with world["app"].app_context():
        disqualification = db.session.scalar(
            db.select(Disqualification).where(Disqualification.user_id == anna)
        )
        assert disqualification.reason == DELETED_REASON
        assert db.session.get(ClubMember, (world["club_id"], anna)) is None
    # Дисквалификация осталась: результаты по-прежнему не в таблице.
    assert results(world["app"].test_client(), meetup_id) == []


def test_last_organizer_cannot_delete_account(world, org):
    assert me(org)["delete_restriction"] == (
        "Сначала передайте роль организатора в клубе «Tyumen | Speedcubing»"
    )

    response = delete_account(org)

    assert response.status_code == 409
    assert error(response)["code"] == "delete_restricted"
    assert get_user(world, user_id_of(world, "org")).login == "org"


def test_organizer_can_delete_account_when_not_last(world, org):
    create_user(world["app"], "org2", ORGANIZER, world["club_id"])
    assert me(org)["delete_restriction"] is None

    assert delete_account(org).status_code == 204


def test_admin_loses_rights_on_deletion(world):
    user_id = create_user(world["app"], "boss")
    with world["app"].app_context():
        db.session.get(User, user_id).is_admin = True
        db.session.commit()

    delete_account(client_for(world["app"], "boss"))

    assert get_user(world, user_id).is_admin is False


def test_account_without_consents_can_be_deleted(world):
    user_id = create_user(world["app"], "newbie")
    with world["app"].app_context():
        db.session.execute(db.delete(UserConsent).where(UserConsent.user_id == user_id))
        db.session.commit()
    client = client_for(world["app"], "newbie")
    assert me(client)["consents_required"] is True

    assert delete_account(client).status_code == 204


# Удаление с сохранённым именем

def consents_of(world, user_id):
    with world["app"].app_context():
        return [
            (c.type, c.version)
            for c in db.session.scalars(db.select(UserConsent).where(UserConsent.user_id == user_id))
        ]


def test_deletion_without_keep_name_leaves_no_consents(world, clients):
    anna = user_id_of(world, "anna")

    delete_account(clients["anna"], keep_name=False)

    assert get_user(world, anna).display_name == DELETED_USER_NAME
    assert consents_of(world, anna) == []


def test_deletion_with_keep_name_keeps_only_name(world, clients):
    anna = user_id_of(world, "anna")
    with world["app"].app_context():
        user = db.session.get(User, anna)
        user.display_name = "Анна Смирнова"
        user.email = "anna@example.com"
        db.session.commit()

    response = delete_account(clients["anna"], keep_name=True)

    assert response.status_code == 204
    user = get_user(world, anna)
    assert user.display_name == "Анна Смирнова"
    assert user.login is None
    assert user.email is None
    assert user.password_hash is None
    assert user.deleted_at is not None
    # Остальные согласия удалены, осталась одна запись: согласие на распространение
    # не отозвано для имени, версия — та, что давал человек.
    assert consents_of(world, anna) == [
        (ConsentType.DELETED_NAME, CONSENT_VERSIONS[ConsentType.PUBLICATION]),
    ]
    assert me(clients["anna"]) is None


def test_keep_name_requires_publication_consent(world):
    user_id = create_user(world["app"], "newbie")
    with world["app"].app_context():
        db.session.execute(db.delete(UserConsent).where(UserConsent.user_id == user_id))
        db.session.commit()

    response = delete_account(client_for(world["app"], "newbie"), keep_name=True)

    assert response.status_code == 422
    assert error(response)["fields"] == {"keep_name": "Вы не давали согласия на публикацию имени"}
    assert get_user(world, user_id).login == "newbie"


def test_kept_name_is_shown_without_profile(world, clients, meetup_id):
    anna = user_id_of(world, "anna")
    solve(clients["anna"], meetup_id, [1000, 1100, 1200, 1300, 1400])
    guest = world["app"].test_client()

    delete_account(clients["anna"], keep_name=True)

    row = results(guest, meetup_id)[0]
    assert row["user"] == {"id": anna, "display_name": "Иван Петров", "has_profile": False}
    single = club_records(guest, world)["333"]["single"]
    assert single["user"] == {"id": anna, "display_name": "Иван Петров", "has_profile": False}
    assert guest.get(f"/api/users/{anna}").status_code == 404
    assert guest.get(f"/api/users/{anna}/meetups").status_code == 404


def test_login_of_kept_name_account_is_free(world, clients):
    anna = user_id_of(world, "anna")
    delete_account(clients["anna"], keep_name=True)

    response = world["app"].test_client().post("/api/auth/register", json={
        "display_name": "Новая Анна",
        "login": "Anna",
        "password": PASSWORD,
        "consents": {t.value: v for t, v in CONSENT_VERSIONS.items()},
    })

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["user"]["id"] != anna
    assert get_user(world, anna).display_name == "Иван Петров"
