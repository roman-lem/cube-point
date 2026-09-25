"""Модели БД. Схема описана в разделе «Модель данных» CLAUDE.md.

Удаление:
- вниз по иерархии владения (встреча → дисциплины → серии → попытки) — каскадное;
- клуб со встречами удалить нельзя (RESTRICT), сначала удаляются встречи;
- пользователя с результатами удалить нельзя (RESTRICT): удаление аккаунта
  обезличивает его (accounts.delete_account), а результаты остаются;
- служебные ссылки «кто сделал» (created_by, decided_by и т. п.) обнуляются.

Результаты (value, best, average) — целые числа, DNF = -1 (см. results.py),
NULL — результата нет.
"""

import enum
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates

from .events import EVENTS
from .extensions import db


def utcnow():
    # Метки времени храним в UTC без часового пояса: SQLite его всё равно теряет.
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


# Цвета логотипа клуба (кружок с первой буквой названия). Сами цвета —
# CSS-переменные --color-logo-* на фронте.
CLUB_COLORS = ("blue", "sky", "teal", "amber", "orange", "rose", "slate", "brown")


class ConsentType(enum.StrEnum):
    PROCESSING = "processing"    # согласие на обработку персональных данных
    PUBLICATION = "publication"  # согласие на распространение (публикацию)


class RecordType(enum.StrEnum):
    SINGLE = "single"
    AVERAGE = "average"


def enum_type(enum_class):
    """Enum в БД: строка со значением (не именем) и CHECK на допустимые значения."""
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


# Имя удалённого аккаунта в таблицах и профиле (accounts.delete_account).
DELETED_USER_NAME = "Удалённый участник"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # login и password_hash — NULL только у удалённого аккаунта.
    login = db.Column(db.String(32), unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255))
    email = db.Column(db.String(254), unique=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
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

    def get_id(self):
        # Версия сессии в идентификаторе: при её увеличении все сессии
        # и remember-куки пользователя перестают действовать (см. auth.load_user).
        return f"{self.id}:{self.session_version}"


class UserConsent(db.Model):
    """Согласие пользователя: какое, какой версии текста и когда дано.

    Записи только добавляются (новая версия текста — новая запись),
    удаляются вместе с аккаунтом. Текущие версии — consents.CONSENT_VERSIONS.
    """

    __tablename__ = "user_consents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, user_fk("CASCADE"), nullable=False, index=True)
    type = db.Column(enum_type(ConsentType), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Club(db.Model):
    __tablename__ = "clubs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    timezone = db.Column(db.String(64), nullable=False)  # например, Asia/Yekaterinburg
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
        # Список встреч клуба и выборки для рекордов клуба.
        db.Index("ix_meetups_club_id_date", "club_id", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # RESTRICT: клуб со встречами удалить нельзя, чтобы не потерять результаты.
    club_id = db.Column(
        db.Integer, db.ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False,
    )
    date = db.Column(db.Date, nullable=False)  # дата в часовом поясе клуба
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
        "MeetupEvent", back_populates="meetup", order_by="MeetupEvent.id",
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
    # Идентификатор из EVENTS. Без CHECK в БД, чтобы новая дисциплина
    # не требовала миграции.
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
    # Оптимистичная блокировка: SQLAlchemy сам увеличивает version при UPDATE
    # и бросает StaleDataError, если серию успел изменить кто-то другой.
    version = db.Column(db.Integer, nullable=False)
    # Кеш подсчёта из results.calc_series, пересчитывается при сохранении.
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
    # Сотые доли секунды или число ходов (FMC), без штрафа.
    value = db.Column(db.Integer)
    penalty = db.Column(enum_type(Penalty), nullable=False, default=Penalty.NONE)
    solution = db.Column(db.Text)  # только FMC
    # Момент сдачи, не меняется при правке. Используется для рекордов.
    submitted_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime)
    entered_by = db.Column(db.Integer, user_fk("SET NULL"))

    history = db.relationship(
        "AttemptHistory", order_by="(AttemptHistory.changed_at, AttemptHistory.id)",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class AttemptHistory(db.Model):
    """Журнал попытки: значение после каждого создания и изменения.

    Записи только добавляются (scoring.save_attempt). Первая — исходный результат.
    Журнал удаляется только вместе с попыткой (стирание ошибочного ввода организатора).
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
    """Попытка FMC до сдачи: старт отсчёта, черновик и заморозка решения.

    Строка остаётся и после сдачи, результат и решение — в attempts.
    Правила — раздел «FMC» CLAUDE.md.
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
    # Заморозка сдачи: NULL — решение не сдавали или вернулись к нему.
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
    """Кеш рекордов клуба, полностью пересчитывается функцией recalc_records."""

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


class LoginFailure(db.Model):
    """Неудачная попытка входа, для ограничения перебора паролей (auth/throttle.py)."""

    __tablename__ = "login_failures"
    __table_args__ = (db.Index("ix_login_failures_login_created_at", "login", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    # Логин как его ввели (в нижнем регистре), пользователя с таким логином может не быть.
    login = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
