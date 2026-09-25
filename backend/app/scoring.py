"""Сохранение результатов, рекорды клуба и таблица дисциплины на встрече.

save_attempt — единственное место, где сохраняются результаты: через неё
проходят сдача попытки участником, правки организатора и DNS при завершении
встречи. delete_attempt — стирание ошибочно введённой попытки организатором. Правила — в разделах «Рекорды» и «Одновременная
запись» CLAUDE.md.
"""

from sqlalchemy.orm import attributes, selectinload

from .errors import ApiError
from .events import EVENTS
from .extensions import db
from .models import (
    Attempt, ClubRecord, Disqualification, Format, Meetup, MeetupEvent, Penalty,
    RecordType, Series, SeriesStatus, utcnow,
)
from .results import ATTEMPTS_COUNT, DNF, PLUS_TWO, calc_series

AVERAGE_FORMATS = (Format.AO5, Format.MO3)


class VersionConflict(ApiError):
    def __init__(self):
        super().__init__(
            409, "version_conflict", "Серию успели изменить, данные обновлены",
        )


# Сохранение

def save_attempt(
    series, number, value, penalty, expected_version, user,
    solution=None, submitted_at=None,
):
    """Создаёт или меняет попытку серии, пересчитывает серию и рекорды клуба.

    Проверка версии: если серию изменили после того, как клиент её прочитал,
    бросает VersionConflict. Права и порядок попыток проверяет вызывающий.
    solution — текст решения FMC (None — не менять), submitted_at — момент
    сдачи новой попытки, если это не «сейчас» (заморозка решения FMC).
    """
    if expected_version != series.version:
        raise VersionConflict()

    attempt = next((a for a in series.attempts if a.attempt_number == number), None)
    if attempt is None:
        # submitted_at проставляется только при создании и потом не меняется.
        attempt = Attempt(attempt_number=number, submitted_at=submitted_at or utcnow())
        series.attempts.append(attempt)
    else:
        attempt.updated_at = utcnow()
    attempt.value = value
    attempt.penalty = penalty
    attempt.entered_by = user.id
    if solution is not None:
        attempt.solution = solution

    meetup_event = series.meetup_event
    recalc_series(series, meetup_event)
    # Версия растёт при каждом сохранении, даже если best и average не изменились:
    # иначе SQLAlchemy не обновит строку серии и параллельная запись пройдёт.
    attributes.flag_modified(series, "status")
    db.session.flush()

    recalc_records(meetup_event.meetup.club_id, meetup_event.event_id)


def delete_attempt(series, number, expected_version):
    """Стирает последнюю попытку серии (ошибочный ввод организатора).

    Только последнюю: пропуск в середине сломал бы порядок попыток. Серия без
    попыток удаляется целиком, чтобы человек не попал в таблицу и не получил
    DNS при завершении встречи. Исключение — начатые попытки FMC: момент старта
    остаётся, иначе участник получил бы новый час. Возвращает False, если серия удалена.
    """
    if expected_version != series.version:
        raise VersionConflict()
    if number != len(series.attempts):
        raise ApiError(
            409, "not_last_attempt",
            "Стереть можно только последнюю попытку серии — сначала сотрите следующие",
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


def recalc_series(series, meetup_event):
    """Кеш best и average серии и её статус по введённым попыткам."""
    count = ATTEMPTS_COUNT[meetup_event.format.value]
    attempts = [None] * count
    for attempt in series.attempts:
        attempts[attempt.attempt_number - 1] = attempt_dict(attempt)
    # calc_series ждёт несобранные попытки только в конце списка.
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


# Лучшие результаты: рекорды клуба и личные рекорды

def _not_disqualified():
    return ~db.select(Disqualification.id).where(
        Disqualification.meetup_id == Meetup.id,
        Disqualification.user_id == Series.user_id,
    ).exists()


def _single_query(event_id):
    """Удачные попытки дисциплины в порядке рекорда.

    При равенстве рекорд за тем, кто поставил его первым: дата встречи,
    затем момент сдачи попытки.
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
            _not_disqualified(),
        )
    )
    return query, order


def _average_query(event_id):
    """Средние дисциплины (без DNF) в порядке рекорда.

    Момент получения среднего — сдача последней попытки серии.
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
            Series.average.is_not(None),
            Series.average != DNF,
            _not_disqualified(),
        )
    )
    return query, order


RECORD_QUERIES = {RecordType.SINGLE: _single_query, RecordType.AVERAGE: _average_query}


def recalc_records(club_id, event_id):
    """Полностью пересчитывает кеш рекордов клуба (сингл и среднее) в дисциплине."""
    for record_type, make_query in RECORD_QUERIES.items():
        query, order = make_query(event_id)
        best = db.session.execute(
            query.where(Meetup.club_id == club_id).order_by(*order).limit(1)
        ).first()
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
    """Серии, в которых поставлены личные рекорды: {user_id: series_id}.

    PB считается по всем встречам человека во всех клубах.
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


# Таблица дисциплины

def _result_key(value):
    # Любой результат лучше DNF, DNF лучше отсутствия результата.
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
    """Порядок строк таблицы и места: [(место или None, серия)].

    1. Завершённые серии с удачной попыткой — с местами, при равенстве место общее.
    2. Завершённые серии, где все попытки DNF, — без места.
    3. Незавершённые — без места, по лучшей попытке, затем по числу попыток.
    Внутри равных — по имени.
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
    """Строки таблицы дисциплины: [{"place", "series", "marks"}].

    marks — отметки рекордов у сингла и среднего: списки из "LR" и "PB".
    Только актуальные рекорды. Дисквалифицированные в таблицу не попадают.
    """
    meetup = meetup_event.meetup
    disqualified = {d.user_id for d in meetup.disqualifications}
    series_list = [
        s for s in db.session.scalars(
            db.select(Series)
            .where(Series.meetup_event_id == meetup_event.id)
            .options(selectinload(Series.attempts), selectinload(Series.user))
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
