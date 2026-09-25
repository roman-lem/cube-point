"""Публичный список клубов и клуб, куда корень сайта ведёт вошедшего."""

from datetime import date, datetime, timedelta

import pytest

from app.extensions import db
from app.models import (
    Club, ClubMember, Meetup, MeetupParticipant, MeetupStatus, ParticipantStatus, utcnow,
)

from .helpers import MEMBER, ORGANIZER, client_for, create_user


@pytest.fixture
def clubs(app, client):
    """Три клуба: Тюмень и Омск со встречами, Екатеринбург без встреч."""
    with app.app_context():
        ids = []
        for name, city in [
            ("Tyumen | Speedcubing", "Тюмень"),
            ("Speedcubing Omsk", "Омск"),
            ("Кубинг Екатеринбург", "Екатеринбург"),
        ]:
            club = Club(name=name, city=city, timezone="Asia/Yekaterinburg")
            db.session.add(club)
            db.session.flush()
            ids.append(club.id)
        db.session.commit()
        return dict(zip(["tyumen", "omsk", "ekb"], ids))


def add_meetup(app, club_id, day, status=MeetupStatus.FINISHED):
    with app.app_context():
        meetup = Meetup(
            club_id=club_id, date=day, status=status,
            starts_at=datetime.combine(day, datetime.min.time()) + timedelta(hours=10),
        )
        db.session.add(meetup)
        db.session.commit()
        return meetup.id


def approve(app, meetup_id, user_id):
    with app.app_context():
        db.session.add(MeetupParticipant(
            meetup_id=meetup_id, user_id=user_id, status=ParticipantStatus.APPROVED,
        ))
        db.session.commit()


def join(app, club_id, user_id, joined_at=None):
    with app.app_context():
        db.session.add(ClubMember(
            club_id=club_id, user_id=user_id, role=MEMBER, joined_at=joined_at or utcnow(),
        ))
        db.session.commit()


def home_club(client):
    response = client.get("/api/auth/home-club")
    assert response.status_code == 200
    return response.get_json()["club_id"]


def test_list_counts_and_order(app, clubs):
    create_user(app, "a", MEMBER, clubs["omsk"])
    create_user(app, "b", MEMBER, clubs["omsk"])
    create_user(app, "banned", MEMBER, clubs["omsk"], banned=True)
    create_user(app, "c", ORGANIZER, clubs["tyumen"])
    add_meetup(app, clubs["omsk"], date(2026, 9, 5))
    add_meetup(app, clubs["tyumen"], date(2026, 9, 1))
    add_meetup(app, clubs["tyumen"], date(2026, 9, 12), MeetupStatus.LIVE)
    # Запланированная встреча не считается и не двигает клуб вверх.
    add_meetup(app, clubs["omsk"], date(2026, 12, 1), MeetupStatus.PLANNED)

    body = app.test_client().get("/api/clubs").get_json()

    summary = [
        (c["name"], c["member_count"], c["meetup_count"], c["last_meetup_date"])
        for c in body["clubs"]
    ]
    assert summary == [
        ("Tyumen | Speedcubing", 1, 2, "2026-09-12"),
        ("Speedcubing Omsk", 2, 1, "2026-09-05"),
        ("Кубинг Екатеринбург", 0, 0, None),
    ]


def test_guest_has_no_home_club(app, clubs):
    assert home_club(app.test_client()) is None


def test_user_without_clubs_has_no_home_club(app, clubs):
    create_user(app, "newbie")

    assert home_club(client_for(app, "newbie")) is None


def test_home_club_is_club_of_last_meetup(app, clubs):
    user_id = create_user(app, "ivan", MEMBER, clubs["tyumen"])
    join(app, clubs["omsk"], user_id)
    approve(app, add_meetup(app, clubs["tyumen"], date(2026, 9, 1)), user_id)
    approve(app, add_meetup(app, clubs["omsk"], date(2026, 9, 5)), user_id)
    # Заявка не подтверждена — это не его встреча.
    with app.app_context():
        db.session.add(MeetupParticipant(
            meetup_id=add_meetup(app, clubs["tyumen"], date(2026, 9, 12)), user_id=user_id,
        ))
        db.session.commit()

    assert home_club(client_for(app, "ivan")) == clubs["omsk"]


def test_home_club_skips_clubs_user_left(app, clubs):
    user_id = create_user(app, "ivan", MEMBER, clubs["tyumen"])
    approve(app, add_meetup(app, clubs["omsk"], date(2026, 9, 5)), user_id)

    assert home_club(client_for(app, "ivan")) == clubs["tyumen"]


def test_home_club_without_meetups_is_last_joined(app, clubs):
    user_id = create_user(app, "org", ORGANIZER, clubs["tyumen"])
    join(app, clubs["ekb"], user_id, joined_at=utcnow() + timedelta(minutes=1))

    assert home_club(client_for(app, "org")) == clubs["ekb"]
