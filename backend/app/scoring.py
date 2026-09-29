"""Saving results, club records and the event table of a meetup.

save_attempt is the only place where results are saved: it handles
attempts submitted by participants, organizer edits, restoring the original
result and DNS on meetup finish. It also keeps the attempt history
(attempt_history). delete_attempt erases an attempt entered by mistake
by an organizer. Rules: "Records", "Organizer desk"
and "Concurrent edits" in docs/ARCHITECTURE.md.
"""

from flask_login import current_user
from sqlalchemy.orm import attributes, selectinload

from .errors import ApiError
from .events import EVENTS
from .extensions import db
from .models import (
    Attempt, AttemptHistory, ClubRecord, Disqualification, Format, Meetup, MeetupEvent,
    MeetupStatus, Penalty, RecordType, Series, SeriesStatus, utcnow,
)
from .results import ATTEMPTS_COUNT, DNF, PLUS_TWO, calc_series

AVERAGE_FORMATS = (Format.AO5, Format.MO3)


class VersionConflict(ApiError):
    def __init__(self):
        super().__init__(
            409, "version_conflict", "Серию успели изменить, данные обновлены",
        )


# Saving

def save_attempt(
    series, number, value, penalty, expected_version, user,
    solution=None, submitted_at=None,
):
    """Creates or changes an attempt of a series, recalculates the series and club records.

    Version check: if the series changed after the client read it,
    raises VersionConflict. Permissions and attempt order are checked by the caller.
    solution is the FMC solution text (None: leave unchanged), submitted_at is the
    submission moment of a new attempt if it is not "now" (frozen FMC solution).

    Every creation and change adds an entry to the attempt history. Saving
    the same value touches neither the attempt nor the history.
    """
    if expected_version != series.version:
        raise VersionConflict()

    attempt = next((a for a in series.attempts if a.attempt_number == number), None)
    if solution is None and attempt is not None:
        solution = attempt.solution
    if attempt is None:
        # submitted_at is set only on creation and never changes afterwards.
        attempt = Attempt(attempt_number=number, submitted_at=submitted_at or utcnow())
        series.attempts.append(attempt)
        changed = True
    else:
        changed = (attempt.value, attempt.penalty, attempt.solution) != (value, penalty, solution)
        if changed:
            attempt.updated_at = utcnow()
    if changed:
        attempt.value = value
        attempt.penalty = penalty
        attempt.solution = solution
        attempt.entered_by = user.id
        attempt.history.append(AttemptHistory(
            value=value, penalty=penalty, solution=solution,
            changed_by=user.id, changed_at=utcnow(),
        ))

    meetup_event = series.meetup_event
    recalc_series(series, meetup_event)
    # The version grows on every save, even if best and average did not change:
    # otherwise SQLAlchemy would not update the series row and a concurrent write would pass.
    attributes.flag_modified(series, "status")
    db.session.flush()

    recalc_records(meetup_event.meetup.club_id, meetup_event.event_id)


def delete_attempt(series, number, expected_version):
    """Erases the last attempt of a series (an organizer's mistaken entry).

    Only the last one: a gap in the middle would break the attempt order. A series without
    attempts is deleted entirely, so the person does not appear in the table or get
    DNS on meetup finish. Exception: started FMC attempts, whose start moment
    is kept, otherwise the participant would get a new hour. Returns False if the series was deleted.

    An attempt submitted by the participant cannot be erased, only corrected: otherwise
    its history with the original result would be lost along with it.
    """
    if expected_version != series.version:
        raise VersionConflict()
    if number != len(series.attempts):
        raise ApiError(
            409, "not_last_attempt",
            "Стереть можно только последнюю попытку серии — сначала сотрите следующие",
        )
    if is_participant_attempt(series, series.attempts[-1]):
        raise ApiError(
            409, "participant_attempt",
            "Попытку сдал сам участник — её можно исправить, но не стереть",
        )

    meetup_event = series.meetup_event
    series.attempts.pop()
    kept = bool(series.attempts or series.fmc_attempts)
    if kept:
        series.status = SeriesStatus.IN_PROGRESS
        series.completed_at = None
        recalc_series(series, meetup_event)
        attributes.flag_modified(series, "status")
    else:
        db.session.delete(series)
    db.session.flush()

    recalc_records(meetup_event.meetup.club_id, meetup_event.event_id)
    return kept


def is_participant_attempt(series, attempt):
    """The attempt was submitted by the participant: the first history entry is by the series owner."""
    return bool(attempt.history) and attempt.history[0].changed_by == series.user_id


def recalc_series(series, meetup_event):
    """Cached best and average of the series and its status from the entered attempts."""
    count = ATTEMPTS_COUNT[meetup_event.format.value]
    attempts = [None] * count
    for attempt in series.attempts:
        attempts[attempt.attempt_number - 1] = attempt_dict(attempt)
    # calc_series expects attempts not yet done only at the end of the list.
    while attempts and attempts[-1] is None:
        attempts.pop()

    result = calc_series(
        attempts, meetup_event.format.value, EVENTS[meetup_event.event_id].result_type,
    )
    series.best = result["best"]
    series.average = result["average"]
    if len(series.attempts) == count and series.status != SeriesStatus.COMPLETED:
        series.status = SeriesStatus.COMPLETED
        series.completed_at = utcnow()


def attempt_dict(attempt):
    return {"value": attempt.value, "penalty": attempt.penalty.value}


def solution_visible(series):
    """Whether the current user may see the FMC solutions of the series.

    While the meetup is not finished, only the series owner sees them, so nobody
    can peek, organizers included. After the meetup is finished they are public.
    The only exception is the meetup finish dialog (desk.finish_summary).
    """
    if series.meetup_event.meetup.status == MeetupStatus.FINISHED:
        return True
    return current_user.is_authenticated and current_user.id == series.user_id


def serialize_attempt(attempt, show_solution=False):
    """Attempt for tables: a corrected one gets a mark and the original value.

    Corrected means more than one history entry. The original value
    is visible to everyone, the full history (who and when) only to organizers.
    show_solution adds the FMC solution text (see solution_visible).
    """
    item = attempt_dict(attempt)
    if show_solution and attempt.solution is not None:
        item["solution"] = attempt.solution
    if len(attempt.history) > 1:
        original = attempt.history[0]
        item["edited"] = True
        item["original"] = {"value": original.value, "penalty": original.penalty.value}
    return item


# Best results: club records and personal bests

def not_disqualified():
    """Condition for a query with Series and Meetup: the participant is not disqualified at the meetup."""
    return ~db.select(Disqualification.id).where(
        Disqualification.meetup_id == Meetup.id,
        Disqualification.user_id == Series.user_id,
    ).exists()


def _single_query(event_id):
    """Successful attempts of an event in record order.

    On ties the record belongs to whoever set it first: meetup date,
    then the attempt's submission moment.
    """
    value = db.case(
        (Attempt.penalty == Penalty.PLUS2, Attempt.value + PLUS_TWO), else_=Attempt.value,
    )
    order = (value, Meetup.date, Attempt.submitted_at, Attempt.id)
    query = (
        db.select(
            Series.user_id, Series.id.label("series_id"), value.label("value"),
            Attempt.submitted_at.label("achieved_at"),
        )
        .select_from(Attempt)
        .join(Series, Attempt.series_id == Series.id)
        .join(MeetupEvent, Series.meetup_event_id == MeetupEvent.id)
        .join(Meetup, MeetupEvent.meetup_id == Meetup.id)
        .where(
            MeetupEvent.event_id == event_id,
            Attempt.penalty.in_([Penalty.NONE, Penalty.PLUS2]),
            not_disqualified(),
        )
    )
    return query, order


def _average_query(event_id):
    """Averages of an event (without DNF) in record order.

    Only formats with an average (ao5, mo3) have averages; bo formats have only singles.
    The moment an average is achieved is the submission of the series' last attempt.
    """
    last_submitted = (
        db.select(db.func.max(Attempt.submitted_at))
        .where(Attempt.series_id == Series.id)
        .scalar_subquery()
    )
    order = (Series.average, Meetup.date, last_submitted, Series.id)
    query = (
        db.select(
            Series.user_id, Series.id.label("series_id"), Series.average.label("value"),
            last_submitted.label("achieved_at"),
        )
        .select_from(Series)
        .join(MeetupEvent, Series.meetup_event_id == MeetupEvent.id)
        .join(Meetup, MeetupEvent.meetup_id == Meetup.id)
        .where(
            MeetupEvent.event_id == event_id,
            MeetupEvent.format.in_(AVERAGE_FORMATS),
            Series.average.is_not(None),
            Series.average != DNF,
            not_disqualified(),
        )
    )
    return query, order


RECORD_QUERIES = {RecordType.SINGLE: _single_query, RecordType.AVERAGE: _average_query}


def best_result(event_id, record_type, *conditions):
    """Best result of an event among those selected by the conditions, or None.

    Row: user_id, series_id, value, achieved_at.
    """
    query, order = RECORD_QUERIES[record_type](event_id)
    return db.session.execute(query.where(*conditions).order_by(*order).limit(1)).first()


def recalc_records(club_id, event_id):
    """Fully recalculates the club records cache (single and average) for an event."""
    for record_type in RecordType:
        best = best_result(event_id, record_type, Meetup.club_id == club_id)
        record = db.session.get(ClubRecord, (club_id, event_id, record_type))
        if best is None:
            if record:
                db.session.delete(record)
            continue
        if record is None:
            record = ClubRecord(club_id=club_id, event_id=event_id, type=record_type)
            db.session.add(record)
        record.user_id = best.user_id
        record.series_id = best.series_id
        record.value = best.value
        record.achieved_at = best.achieved_at


def personal_record_series(event_id, record_type, user_ids):
    """Series holding personal bests: {user_id: series_id}.

    PB is computed over all of the person's meetups in all clubs.
    """
    if not user_ids:
        return {}
    query, order = RECORD_QUERIES[record_type](event_id)
    number = db.func.row_number().over(partition_by=Series.user_id, order_by=order)
    ranked = query.add_columns(number.label("number")).where(
        Series.user_id.in_(user_ids)
    ).subquery()
    rows = db.session.execute(
        db.select(ranked.c.user_id, ranked.c.series_id).where(ranked.c.number == 1)
    ).all()
    return dict(rows)


# Event table

def _result_key(value):
    # Any result is better than DNF, DNF is better than no result.
    if value is None:
        return (2, 0)
    if value == DNF:
        return (1, 0)
    return (0, value)


def ranking_key(series, series_format):
    if series_format in AVERAGE_FORMATS:
        return (_result_key(series.average), _result_key(series.best))
    return (_result_key(series.best),)


def rank(series_list, series_format):
    """Order of table rows and places: [(place or None, series)].

    1. Finished series with a successful attempt get places; ties share a place.
    2. Finished series where all attempts are DNF get no place.
    3. Unfinished series get no place, sorted by best attempt, then by number of attempts.
    Ties are sorted by name.
    """
    series_list = sorted(series_list, key=lambda s: s.user.display_name)
    completed = [s for s in series_list if s.status == SeriesStatus.COMPLETED]
    ranked = sorted(
        (s for s in completed if s.best not in (None, DNF)),
        key=lambda s: ranking_key(s, series_format),
    )
    all_dnf = [s for s in completed if s.best in (None, DNF)]
    in_progress = sorted(
        (s for s in series_list if s.status != SeriesStatus.COMPLETED),
        key=lambda s: (_result_key(s.best), -len(s.attempts)),
    )

    rows = []
    place, previous_key = None, None
    for index, series in enumerate(ranked, 1):
        key = ranking_key(series, series_format)
        if key != previous_key:
            place, previous_key = index, key
        rows.append((place, series))
    rows.extend((None, series) for series in all_dnf + in_progress)
    return rows


def event_table(meetup_event):
    """Event table rows: [{"place", "series", "marks"}].

    marks are record marks of the single and the average: lists of "LR" and "PB".
    Current records only. Disqualified participants are not in the table.
    """
    meetup = meetup_event.meetup
    disqualified = {d.user_id for d in meetup.disqualifications}
    series_list = [
        s for s in db.session.scalars(
            db.select(Series)
            .where(Series.meetup_event_id == meetup_event.id)
            .options(
                selectinload(Series.attempts).selectinload(Attempt.history),
                selectinload(Series.user),
            )
        )
        if s.user_id not in disqualified
    ]

    user_ids = [s.user_id for s in series_list]
    club_records = {
        record.type: record.series_id
        for record in db.session.scalars(db.select(ClubRecord).where(
            ClubRecord.club_id == meetup.club_id,
            ClubRecord.event_id == meetup_event.event_id,
        ))
    }
    personal = {
        record_type: personal_record_series(meetup_event.event_id, record_type, user_ids)
        for record_type in RecordType
    }

    def marks(series, record_type):
        result = []
        if club_records.get(record_type) == series.id:
            result.append("LR")
        if personal[record_type].get(series.user_id) == series.id:
            result.append("PB")
        return result

    return [
        {
            "place": place,
            "series": series,
            "marks": {
                "single": marks(series, RecordType.SINGLE),
                "average": marks(series, RecordType.AVERAGE),
            },
        }
        for place, series in rank(series_list, meetup_event.format)
    ]
