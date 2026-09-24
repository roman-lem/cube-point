"""Ограничения схемы и поведение при удалении."""

from datetime import date, datetime

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app import create_app
from app.extensions import db
from app.models import (
    Attempt, Club, ClubMember, ClubRecord, Disqualification, Format, Meetup,
    MeetupEvent, MeetupParticipant, Penalty, RecordType, Scramble, Series, User,
)

START = datetime(2026, 9, 5, 7, 0)


def make_user(session, login="ivan"):
    user = User(login=login, display_name="Иван Иванов", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def make_meetup(session, club=None, created_by=None):
    club = club or Club(name="Клуб", city="Тюмень", timezone="Asia/Yekaterinburg")
    meetup = Meetup(club=club, date=date(2026, 9, 5), starts_at=START, created_by=created_by)
    session.add(meetup)
    session.flush()
    return meetup


def make_series(session, user, meetup=None, event_id="333"):
    meetup = meetup or make_meetup(session)
    meetup_event = MeetupEvent(meetup=meetup, event_id=event_id, format=Format.AO5)
    series = Series(meetup_event=meetup_event, user_id=user.id)
    series.attempts.append(Attempt(attempt_number=1, value=1234))
    session.add(series)
    session.flush()
    return series


def count(session, model):
    return session.scalar(sa.select(sa.func.count()).select_from(model))


def delete(session, model, id_):
    # Удаление SQL-запросом, а не через ORM: проверяем ON DELETE в самой БД.
    session.execute(sa.delete(model).where(model.id == id_))


# Уникальность и проверки


def test_one_series_per_user_in_event(session):
    user = make_user(session)
    series = make_series(session, user)

    session.add(Series(meetup_event_id=series.meetup_event_id, user_id=user.id))
    with pytest.raises(IntegrityError):
        session.flush()


def test_one_attempt_per_number_in_series(session):
    series = make_series(session, make_user(session))

    session.add(Attempt(series_id=series.id, attempt_number=1, value=1500))
    with pytest.raises(IntegrityError):
        session.flush()


def test_same_user_can_have_series_in_different_events(session):
    user = make_user(session)
    series = make_series(session, user)

    make_series(session, user, meetup=series.meetup_event.meetup, event_id="222")

    assert count(session, Series) == 2


def test_event_is_unique_in_meetup(session):
    meetup = make_meetup(session)
    meetup.events.append(MeetupEvent(event_id="333", format=Format.AO5))
    meetup.events.append(MeetupEvent(event_id="333", format=Format.MO3))

    with pytest.raises(IntegrityError):
        session.flush()


def test_scramble_number_is_unique_in_event(session):
    meetup = make_meetup(session)
    meetup_event = MeetupEvent(meetup=meetup, event_id="333", format=Format.AO5)
    meetup_event.scrambles = [
        Scramble(attempt_number=1, scramble="R U"),
        Scramble(attempt_number=1, scramble="F D"),
    ]
    session.add(meetup_event)

    with pytest.raises(IntegrityError):
        session.flush()


def test_unknown_event_is_rejected():
    with pytest.raises(ValueError):
        MeetupEvent(event_id="444", format=Format.AO5)


def test_login_is_stored_lowercase_and_unique(session):
    user = make_user(session, login="IvanPetrov")
    assert user.login == "ivanpetrov"

    session.add(User(login="IVANPETROV", display_name="Другой", password_hash="hash"))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("value, penalty", [
    (None, Penalty.NONE),   # без DNF/DNS нужно время
    (None, Penalty.PLUS2),
    (0, Penalty.NONE),      # время больше нуля
    (-1, Penalty.DNF),      # DNF не хранится как -1 в попытке
])
def test_invalid_attempt_value(session, value, penalty):
    series = make_series(session, make_user(session))

    session.add(Attempt(series_id=series.id, attempt_number=2, value=value, penalty=penalty))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("value, penalty", [(None, Penalty.DNS), (None, Penalty.DNF), (1500, Penalty.DNF)])
def test_dnf_and_dns_may_have_no_value(session, value, penalty):
    series = make_series(session, make_user(session))

    session.add(Attempt(series_id=series.id, attempt_number=2, value=value, penalty=penalty))
    session.flush()


def test_attempt_number_is_from_1_to_5(session):
    series = make_series(session, make_user(session))

    session.add(Attempt(series_id=series.id, attempt_number=6, value=1500))
    with pytest.raises(IntegrityError):
        session.flush()


def test_series_version_detects_concurrent_change(session):
    series = make_series(session, make_user(session))
    session.commit()
    assert series.version == 1

    # Кто-то другой уже сохранил серию.
    session.execute(sa.text("UPDATE series SET version = 2 WHERE id = :id"), {"id": series.id})
    series.best = 1234
    with pytest.raises(StaleDataError):
        session.flush()


# Удаление


def test_deleting_series_deletes_attempts(session):
    series = make_series(session, make_user(session))

    delete(session, Series, series.id)

    assert count(session, Attempt) == 0


def test_deleting_meetup_deletes_everything_inside(session):
    user = make_user(session)
    series = make_series(session, user)
    meetup = series.meetup_event.meetup
    series.meetup_event.scrambles = [Scramble(attempt_number=1, scramble="R U")]
    session.add_all([
        MeetupParticipant(meetup_id=meetup.id, user_id=user.id),
        Disqualification(meetup_id=meetup.id, user_id=user.id, reason="Причина"),
    ])
    session.flush()

    delete(session, Meetup, meetup.id)

    for model in (MeetupEvent, Scramble, Series, Attempt, MeetupParticipant, Disqualification):
        assert count(session, model) == 0, model.__name__
    assert count(session, User) == 1
    assert count(session, Club) == 1


def test_club_with_meetups_cannot_be_deleted(session):
    meetup = make_meetup(session)

    with pytest.raises(IntegrityError):
        delete(session, Club, meetup.club_id)


def test_deleting_club_deletes_members_and_records(session):
    user = make_user(session)
    series = make_series(session, user)
    meetup = series.meetup_event.meetup
    club_id = meetup.club_id
    session.add_all([
        ClubMember(club_id=club_id, user_id=user.id),
        ClubRecord(
            club_id=club_id, event_id="333", type=RecordType.SINGLE, user_id=user.id,
            value=1234, series_id=series.id, achieved_at=START,
        ),
    ])
    session.flush()

    delete(session, Meetup, meetup.id)  # сначала встречи — иначе RESTRICT
    delete(session, Club, club_id)

    assert count(session, ClubMember) == 0
    assert count(session, ClubRecord) == 0


def test_deleting_series_deletes_record_that_points_to_it(session):
    user = make_user(session)
    series = make_series(session, user)
    session.add(ClubRecord(
        club_id=series.meetup_event.meetup.club_id, event_id="333",
        type=RecordType.SINGLE, user_id=user.id, value=1234,
        series_id=series.id, achieved_at=START,
    ))
    session.flush()

    delete(session, Series, series.id)

    assert count(session, ClubRecord) == 0


def test_user_with_results_cannot_be_deleted(session):
    user = make_user(session)
    make_series(session, user)

    with pytest.raises(IntegrityError):
        delete(session, User, user.id)


def test_deleting_author_keeps_their_meetup(session):
    organizer = make_user(session, login="organizer")
    meetup = make_meetup(session, created_by=organizer.id)

    delete(session, User, organizer.id)
    session.expire_all()

    assert meetup.created_by is None


# Миграции и тестовые данные


def test_migrations_match_models(tmp_path):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}"})
    with app.app_context():
        upgrade()
        with db.engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), db.metadata)

    assert diff == []


def test_seed_command(app, session):
    result = app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code == 0, result.output
    assert count(session, User) == 16
    assert count(session, Meetup) == 3
    assert count(session, Disqualification) == 1
    for penalty in Penalty:
        assert session.scalar(
            sa.select(sa.func.count()).select_from(Attempt).where(Attempt.penalty == penalty)
        ) > 0, penalty
    # Кеш рекордов заполнен: сингл и среднее во всех дисциплинах со средним.
    assert count(session, ClubRecord) > 0
