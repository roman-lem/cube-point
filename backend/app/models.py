"""Database models. The schema is described in "Data model" in docs/ARCHITECTURE.md.

Deletion:
- down the ownership hierarchy (meetup → events → series → attempts) it cascades;
- a club with meetups cannot be deleted by accident (RESTRICT): the administrator's
  club deletion (admin.delete_club) deletes the meetups first;
- a user with results cannot be deleted (RESTRICT): account deletion
  anonymizes it (accounts.delete_account) and the results stay;
- auxiliary "who did it" references (created_by, decided_by, etc.) are set to NULL.

Results (value, best, average) are integers, DNF = -1 (see results.py),
NULL means no result.
"""

import enum
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates

from .events import EVENT_ORDER, EVENTS
from .extensions import db


def utcnow():
    # Timestamps are stored in UTC without a time zone: SQLite loses it anyway.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ClubRole(enum.StrEnum):
    MEMBER = "member"
    ORGANIZER = "organizer"


class LinkType(enum.StrEnum):
    VK = "vk"
    YOUTUBE = "youtube"
    SITE = "site"
    OTHER = "other"


class MeetupStatus(enum.StrEnum):
    PLANNED = "planned"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class ParticipantStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Format(enum.StrEnum):
    AO5 = "ao5"
    MO3 = "mo3"
    BO3 = "bo3"
    BO5 = "bo5"
    BO1 = "bo1"


class SeriesStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Penalty(enum.StrEnum):
    NONE = "none"
    PLUS2 = "plus2"
    DNF = "dnf"
    DNS = "dns"


# Club logo colors (a circle with the first letter of the name). The colors themselves
# are the --color-logo-* CSS variables on the frontend.
CLUB_COLORS = ("blue", "sky", "teal", "amber", "orange", "rose", "slate", "brown")


class ConsentType(enum.StrEnum):
    PROCESSING = "processing"    # consent to personal data processing
    PUBLICATION = "publication"  # consent to publication
    # Age confirmation: 14 or older, or the consents are given by a legal representative.
    AGE = "age"
    # A deleted account kept its name in results and records: the processing and
    # publication consents given earlier are not withdrawn for the display name.
    DELETED_NAME = "deleted_name"


class RecordType(enum.StrEnum):
    SINGLE = "single"
    AVERAGE = "average"


def enum_type(enum_class):
    """Enum in the DB: a string with the value (not the name) and a CHECK on allowed values."""
    return db.Enum(
        enum_class,
        native_enum=False,
        create_constraint=True,
        length=16,
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
    )


def user_fk(ondelete):
    return db.ForeignKey("users.id", ondelete=ondelete)


# Name of a deleted account in tables and the profile (accounts.delete_account).
DELETED_USER_NAME = "Удалённый участник"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # login and password_hash are NULL only for a deleted account.
    login = db.Column(db.String(32), unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255))
    # Only a confirmed address (lowercase); one waiting for confirmation is in EmailConfirmation.
    email = db.Column(db.String(254), unique=True)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    created_by = db.Column(db.Integer, user_fk("SET NULL"))
    deleted_at = db.Column(db.DateTime)

    consents = db.relationship(
        "UserConsent", cascade="all, delete-orphan", passive_deletes=True,
    )

    @validates("login")
    def _lower_login(self, key, login):
        return login.lower() if login is not None else None

    @property
    def has_profile(self):
        """Whether there is a public profile: a deleted account that kept its name has none.

        The consent given at deletion covers only the name in result tables
        and records, not a profile with all the meetups.
        """
        return self.deleted_at is None or self.display_name == DELETED_USER_NAME

    def get_id(self):
        # The session version is part of the ID: when it increases, all sessions
        # and remember cookies of the user stop working (see auth.load_user).
        return f"{self.id}:{self.session_version}"


class UserConsent(db.Model):
    """A user's consent: which one, which text version and when it was given.

    Entries are only added (a new text version means a new entry),
    and deleted together with the account. Current versions: consents.CONSENT_VERSIONS.
    The exception is DELETED_NAME: it stays after account deletion until
    the administrator anonymizes the account (admin.anonymize_user).
    """

    __tablename__ = "user_consents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, user_fk("CASCADE"), nullable=False, index=True)
    type = db.Column(enum_type(ConsentType), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class OrganizerPledge(db.Model):
    """An organizer's pledge in a club: which text version and when it was accepted.

    Entries are only added. They stay when the role is removed or the account is
    deleted (evidence of the pledge) and go together with the club.
    Current text and version: pledge.PLEDGE_TEXT, pledge.PLEDGE_VERSION.
    """

    __tablename__ = "organizer_pledges"

    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    user_id = db.Column(db.Integer, user_fk("CASCADE"), nullable=False, index=True)
    version = db.Column(db.String(32), nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Club(db.Model):
    __tablename__ = "clubs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    timezone = db.Column(db.String(64), nullable=False)  # e.g. Asia/Yekaterinburg
    description = db.Column(db.Text)
    logo_path = db.Column(db.String(255))
    logo_color = db.Column(db.String(16), nullable=False, default="blue", server_default="blue")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    links = db.relationship(
        "ClubLink", order_by="ClubLink.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    members = db.relationship(
        "ClubMember", cascade="all, delete-orphan", passive_deletes=True,
    )


class ClubLink(db.Model):
    __tablename__ = "club_links"

    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    type = db.Column(enum_type(LinkType), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)


class ClubMember(db.Model):
    __tablename__ = "club_members"

    club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id = db.Column(
        db.Integer, user_fk("RESTRICT"), primary_key=True, index=True,
    )
    role = db.Column(enum_type(ClubRole), nullable=False, default=ClubRole.MEMBER)
    joined_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    banned_at = db.Column(db.DateTime)
    banned_by = db.Column(db.Integer, user_fk("SET NULL"))
    ban_reason = db.Column(db.Text)

    user = db.relationship("User", foreign_keys=[user_id])


class Meetup(db.Model):
    __tablename__ = "meetups"
    __table_args__ = (
        # Club meetup list and queries for club records.
        db.Index("ix_meetups_club_id_date", "club_id", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # RESTRICT: results are not lost by accident; admin.delete_club deletes meetups first.
    club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False,
    )
    date = db.Column(db.Date, nullable=False)  # date in the club's time zone
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime)
    place = db.Column(db.String(200))
    address = db.Column(db.String(300))
    status = db.Column(
        enum_type(MeetupStatus), nullable=False, default=MeetupStatus.PLANNED,
    )
    finished_at = db.Column(db.DateTime)
    join_token = db.Column(db.String(64), unique=True)
    created_by = db.Column(db.Integer, user_fk("SET NULL"))

    club = db.relationship("Club")
    events = db.relationship(
        "MeetupEvent", back_populates="meetup", order_by=lambda: _events_order(),
        cascade="all, delete-orphan", passive_deletes=True,
    )
    participants = db.relationship(
        "MeetupParticipant", cascade="all, delete-orphan", passive_deletes=True,
    )
    disqualifications = db.relationship(
        "Disqualification", cascade="all, delete-orphan", passive_deletes=True,
    )


class MeetupParticipant(db.Model):
    __tablename__ = "meetup_participants"

    meetup_id = db.Column(
        db.Integer, db.ForeignKey("meetups.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id = db.Column(
        db.Integer, user_fk("RESTRICT"), primary_key=True, index=True,
    )
    status = db.Column(
        enum_type(ParticipantStatus), nullable=False, default=ParticipantStatus.PENDING,
    )
    requested_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    decided_at = db.Column(db.DateTime)
    decided_by = db.Column(db.Integer, user_fk("SET NULL"))

    user = db.relationship("User", foreign_keys=[user_id])


class MeetupEvent(db.Model):
    __tablename__ = "meetup_events"
    __table_args__ = (db.UniqueConstraint("meetup_id", "event_id"),)

    id = db.Column(db.Integer, primary_key=True)
    meetup_id = db.Column(
        db.Integer, db.ForeignKey("meetups.id", ondelete="CASCADE"), nullable=False,
    )
    # ID from EVENTS. No CHECK in the DB, so a new event
    # does not require a migration.
    event_id = db.Column(db.String(16), nullable=False, index=True)
    format = db.Column(enum_type(Format), nullable=False)

    meetup = db.relationship("Meetup", back_populates="events")
    scrambles = db.relationship(
        "Scramble", order_by="Scramble.attempt_number",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    series = db.relationship(
        "Series", back_populates="meetup_event",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    @validates("event_id")
    def _check_event_id(self, key, event_id):
        if event_id not in EVENTS:
            raise ValueError(f"Неизвестная дисциплина: {event_id}")
        return event_id


def _events_order():
    """Meetup events in the WCA order, whatever order they were created in."""
    return [
        db.case(EVENT_ORDER, value=MeetupEvent.event_id, else_=len(EVENT_ORDER)),
        MeetupEvent.id,
    ]


class Scramble(db.Model):
    __tablename__ = "scrambles"
    __table_args__ = (db.UniqueConstraint("meetup_event_id", "attempt_number"),)

    id = db.Column(db.Integer, primary_key=True)
    meetup_event_id = db.Column(
        db.Integer, db.ForeignKey("meetup_events.id", ondelete="CASCADE"), nullable=False,
    )
    attempt_number = db.Column(db.Integer, nullable=False)
    scramble = db.Column(db.Text, nullable=False)


class Series(db.Model):
    __tablename__ = "series"
    __table_args__ = (db.UniqueConstraint("meetup_event_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    meetup_event_id = db.Column(
        db.Integer, db.ForeignKey("meetup_events.id", ondelete="CASCADE"), nullable=False,
    )
    user_id = db.Column(db.Integer, user_fk("RESTRICT"), nullable=False, index=True)
    status = db.Column(
        enum_type(SeriesStatus), nullable=False, default=SeriesStatus.IN_PROGRESS,
    )
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime)
    # Optimistic locking: SQLAlchemy increments version on UPDATE itself
    # and raises StaleDataError if someone else has changed the series.
    version = db.Column(db.Integer, nullable=False)
    # Cache of results.calc_series, recalculated on save.
    best = db.Column(db.Integer)
    average = db.Column(db.Integer)

    __mapper_args__ = {"version_id_col": version}

    meetup_event = db.relationship("MeetupEvent", back_populates="series")
    user = db.relationship("User")
    attempts = db.relationship(
        "Attempt", order_by="Attempt.attempt_number",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    fmc_attempts = db.relationship(
        "FmcAttempt", order_by="FmcAttempt.attempt_number",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class Attempt(db.Model):
    __tablename__ = "attempts"
    __table_args__ = (
        db.UniqueConstraint("series_id", "attempt_number"),
        db.CheckConstraint("attempt_number BETWEEN 1 AND 5", name="attempt_number_range"),
        db.CheckConstraint("value IS NULL OR value > 0", name="value_positive"),
        db.CheckConstraint(
            "penalty IN ('dnf', 'dns') OR value IS NOT NULL", name="value_required",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(
        db.Integer, db.ForeignKey("series.id", ondelete="CASCADE"), nullable=False,
    )
    attempt_number = db.Column(db.Integer, nullable=False)
    # Hundredths of a second or number of moves (FMC), without the penalty.
    value = db.Column(db.Integer)
    penalty = db.Column(enum_type(Penalty), nullable=False, default=Penalty.NONE)
    solution = db.Column(db.Text)  # FMC only
    # Submission moment, does not change on edits. Used for records.
    submitted_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime)
    entered_by = db.Column(db.Integer, user_fk("SET NULL"))

    history = db.relationship(
        "AttemptHistory", order_by="(AttemptHistory.changed_at, AttemptHistory.id)",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class AttemptHistory(db.Model):
    """Attempt history: the value after every creation and change.

    Entries are only added (scoring.save_attempt). The first one is the original result.
    History is deleted only together with the attempt (erasing an organizer's mistaken entry).
    """

    __tablename__ = "attempt_history"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(
        db.Integer, db.ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    value = db.Column(db.Integer)
    penalty = db.Column(enum_type(Penalty), nullable=False)
    solution = db.Column(db.Text)
    changed_by = db.Column(db.Integer, user_fk("SET NULL"))
    changed_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User")


class FmcAttempt(db.Model):
    """An FMC attempt before submission: countdown start, draft and frozen solution.

    The row stays after submission; the result and the solution are in attempts.
    Rules: "FMC" in docs/ARCHITECTURE.md.
    """

    __tablename__ = "fmc_attempts"
    __table_args__ = (
        db.CheckConstraint("attempt_number BETWEEN 1 AND 5", name="attempt_number_range"),
    )

    series_id = db.Column(
        db.Integer, db.ForeignKey("series.id", ondelete="CASCADE"), primary_key=True,
    )
    attempt_number = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    draft = db.Column(db.Text, nullable=False, default="")
    draft_saved_at = db.Column(db.DateTime)
    # Submission freeze: NULL means not submitted or returned to the solution.
    frozen_solution = db.Column(db.Text)
    frozen_at = db.Column(db.DateTime)


class Disqualification(db.Model):
    __tablename__ = "disqualifications"
    __table_args__ = (db.UniqueConstraint("meetup_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    meetup_id = db.Column(
        db.Integer, db.ForeignKey("meetups.id", ondelete="CASCADE"), nullable=False,
    )
    user_id = db.Column(db.Integer, user_fk("RESTRICT"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, user_fk("SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class ClubRecord(db.Model):
    """Club records cache, fully recalculated by recalc_records."""

    __tablename__ = "club_records"

    club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", ondelete="CASCADE"), primary_key=True,
    )
    event_id = db.Column(db.String(16), primary_key=True)
    type = db.Column(enum_type(RecordType), primary_key=True)
    user_id = db.Column(db.Integer, user_fk("RESTRICT"), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    series_id = db.Column(
        db.Integer, db.ForeignKey("series.id", ondelete="CASCADE"), nullable=False,
    )
    achieved_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User")
    series = db.relationship("Series")


class EmailConfirmation(db.Model):
    """A letter sent when a user binds an email (auth/email.py).

    The latest open row (not used, not cancelled) of a user is the address
    waiting for confirmation, and only its link works: a new letter cancels the earlier
    ones. Rows are also the sending log for the rate limits per user and per IP.
    """

    __tablename__ = "email_confirmations"
    __table_args__ = (
        db.Index("ix_email_confirmations_user_id_created_at", "user_id", "created_at"),
        db.Index("ix_email_confirmations_ip_created_at", "ip", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    email = db.Column(db.String(254), nullable=False)
    # SHA-256 of the link token, the token itself is not stored. NULL: the address
    # belongs to another account, the letter said so and has no link.
    token_hash = db.Column(db.String(64), unique=True)
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    # The address was confirmed by this link.
    used_at = db.Column(db.DateTime)
    # A newer letter was sent, the address was cancelled or the letter was not sent.
    cancelled_at = db.Column(db.DateTime)


class PasswordReset(db.Model):
    """A password reset request (auth/password_reset.py).

    A row is written for every request, even for an unknown account (user_id NULL):
    the rows are the log for the rate limits. Only a row with token_hash had a letter
    with a link; the latest open one of a user is the only working link.
    """

    __tablename__ = "password_resets"
    __table_args__ = (
        db.Index("ix_password_resets_user_id_created_at", "user_id", "created_at"),
        db.Index("ix_password_resets_ip_created_at", "ip", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    # SHA-256 of the link token, the token itself is not stored. NULL: no letter was sent.
    token_hash = db.Column(db.String(64), unique=True)
    # The address the letter went to: the link stops working if the email changes.
    email = db.Column(db.String(254))
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    # The password was set by this link.
    used_at = db.Column(db.DateTime)
    # A newer link was sent or the password was reset by another link.
    cancelled_at = db.Column(db.DateTime)


class DisplayNameChange(db.Model):
    """The history of a user's display name (names.py), rows are only added.

    changed_by is the user themselves or an administrator who returned the previous name:
    only the user's own changes count for the rate limit.
    """

    __tablename__ = "display_name_changes"
    __table_args__ = (
        db.Index("ix_display_name_changes_user_id_changed_at", "user_id", "changed_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    old_name = db.Column(db.String(100), nullable=False)
    new_name = db.Column(db.String(100), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    changed_by = db.Column(db.Integer, user_fk("SET NULL"))


class LoginFailure(db.Model):
    """A failed login attempt, for password brute-force protection (auth/throttle.py)."""

    __tablename__ = "login_failures"
    __table_args__ = (
        db.Index("ix_login_failures_login_created_at", "login", "created_at"),
        db.Index("ix_login_failures_ip_created_at", "ip", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # Login as entered (lowercased); a user with this login may not exist.
    login = db.Column(db.String(64), nullable=False)
    # Client address (IPv6 is up to 45 characters). NULL for records made before it was stored.
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Registration(db.Model):
    """A registration journal for the limits (auth/registration.py).

    The IP is kept here, not in users, and only for a day.
    """

    __tablename__ = "registrations"
    __table_args__ = (
        db.Index("ix_registrations_ip_created_at", "ip", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
