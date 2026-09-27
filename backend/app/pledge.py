"""Organizer pledge: accepted once per club before the organizer tools open.

The text lives only here: the frontend gets it from the API (the `pledge` field of
the club and meetup responses). When the text changes, change the version too:
every organizer accepts the new text, the client sends the version it displayed,
and the server accepts only the current one. Checked in permissions.require_organizer.
"""

from .extensions import db
from .models import OrganizerPledge

PLEDGE_VERSION = "2026-09-27"
PLEDGE_TEXT = (
    "Как организатор клуба вы получаете доступ к данным его участников: логинам, "
    "отображаемым именам и результатам. "
    "Обязуюсь использовать эти данные только для "
    "проведения встреч и управления клубом и не передавать их третьим лицам"
)


def pledge_accepted(club_id, user):
    """The user accepted the current pledge text in the club.

    Removing and granting the role again does not ask again while the text is the same.
    """
    return db.session.scalar(
        db.select(OrganizerPledge.id).where(
            OrganizerPledge.club_id == club_id,
            OrganizerPledge.user_id == user.id,
            OrganizerPledge.version == PLEDGE_VERSION,
        ).limit(1)
    ) is not None


def record_pledge(club_id, user):
    db.session.add(OrganizerPledge(club_id=club_id, user_id=user.id, version=PLEDGE_VERSION))
