"""Shared setup for club and meetup API tests."""

from werkzeug.security import generate_password_hash

from app.consents import record_consents
from app.extensions import db
from app.models import Club, ClubMember, ClubRole, User, utcnow
from app.pledge import record_pledge

PASSWORD = "secret-pass"
# Fast hash: speed matters in tests, not strength.
PASSWORD_HASH = generate_password_hash(PASSWORD, method="pbkdf2:sha256:1")


def create_user(app, login, role=None, club_id=None, banned=False, pledge=True):
    """A user (with consents) and, if a role is given, their club membership. Returns the id.

    An organizer has accepted the organizer pledge unless pledge=False.
    """
    with app.app_context():
        user = User(login=login, display_name="Иван Петров", password_hash=PASSWORD_HASH)
        record_consents(user)
        db.session.add(user)
        db.session.flush()
        if role:
            db.session.add(ClubMember(
                club_id=club_id, user_id=user.id, role=role,
                banned_at=utcnow() if banned else None,
            ))
            if role == ClubRole.ORGANIZER and pledge:
                record_pledge(club_id, user)
        db.session.commit()
        return user.id


def create_club(app):
    with app.app_context():
        club = Club(name="Tyumen | Speedcubing", city="Тюмень", timezone="Asia/Yekaterinburg")
        db.session.add(club)
        db.session.commit()
        return club.id


def client_for(app, login):
    """A separate client with a logged-in user."""
    client = app.test_client()
    response = client.post("/api/auth/login", json={"login": login, "password": PASSWORD})
    assert response.status_code == 200
    return client


def error(response):
    return response.get_json()["error"]


ORGANIZER = ClubRole.ORGANIZER
MEMBER = ClubRole.MEMBER
