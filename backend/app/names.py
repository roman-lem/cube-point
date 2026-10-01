"""Display name changes: by the user in the profile settings, at most once per
NAME_CHANGE_INTERVAL, and the previous name returned by an administrator.

The name lives only in users.display_name, so a new name shows everywhere,
in past results and records too. The history (display_name_changes) is seen by
the administrator and the organizers of the user's clubs in the member card.
"""

from datetime import timedelta

from .extensions import db
from .meetups import iso_utc
from .models import DisplayNameChange, utcnow

NAME_CHANGE_INTERVAL = timedelta(days=30)


def last_change(user, own=False):
    query = db.select(DisplayNameChange).where(DisplayNameChange.user_id == user.id)
    if own:
        query = query.where(DisplayNameChange.changed_by == user.id)
    return db.session.scalar(
        query.order_by(DisplayNameChange.changed_at.desc(), DisplayNameChange.id.desc()).limit(1)
    )


def name_change_available_at(user):
    """When the user can change the name again, None if now.

    Only the user's own changes count: a name returned by an administrator
    neither resets nor moves the limit.
    """
    change = last_change(user, own=True)
    if change is None:
        return None
    available_at = change.changed_at + NAME_CHANGE_INTERVAL
    return available_at if available_at > utcnow() else None


def change_name(user, new_name, changed_by):
    db.session.add(DisplayNameChange(
        user_id=user.id, old_name=user.display_name, new_name=new_name,
        changed_at=utcnow(), changed_by=changed_by,
    ))
    user.display_name = new_name


def name_history(user):
    """Name changes, newest first. by_admin: the name was returned by an administrator."""
    changes = db.session.scalars(
        db.select(DisplayNameChange)
        .where(DisplayNameChange.user_id == user.id)
        .order_by(DisplayNameChange.changed_at.desc(), DisplayNameChange.id.desc())
    )
    return [
        {
            "old_name": change.old_name,
            "new_name": change.new_name,
            "changed_at": iso_utc(change.changed_at),
            "by_admin": change.changed_by != user.id,
        }
        for change in changes
    ]
