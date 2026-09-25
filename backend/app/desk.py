"""Панель организатора: ручной ввод и правка результатов, участники,
дисквалификация, завершение встречи и скрамблы для печати.

Адреса: /api/meetups/<id>/desk, …/attempts/<n>, …/participants, …/finish и т. д.
Все действия — только организатору клуба встречи. Правила — разделы «Встречи»,
«Панель организатора» и «Дисквалификация и блокировка» CLAUDE.md.
"""

import secrets

from flask import Blueprint, request
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.security import generate_password_hash

from .auth.validation import login_error, name_error, normalize_login
from .errors import ApiError, ValidationError
from .events import is_fmc
from .extensions import db
from .fmc import MAX_MOVES, parse_solution
from .forms import collapse_spaces, get_str, is_int, json_body, raise_if_errors
from .meetups import approve, get_meetup, iso_utc, serialize_meetup
from .models import (
    ClubMember, Disqualification, MeetupParticipant, MeetupStatus, ParticipantStatus,
    Penalty, Series, SeriesStatus, User, utcnow,
)
from .permissions import is_banned, require_organizer
from .results import ATTEMPTS_COUNT
from .scoring import (
    VersionConflict, delete_attempt, event_table, recalc_records, save_attempt, serialize_attempt,
)
from .series import fmc_deadline, get_meetup_event, parse_value

desk = Blueprint("desk", __name__)

# Организатор ставит любой штраф, в том числе DNS. В FMC штрафа +2 нет.
TIME_PENALTIES = {p.value for p in Penalty}
FMC_PENALTIES = TIME_PENALTIES - {Penalty.PLUS2.value}
MAX_REASON_LENGTH = 500
# Временный пароль: без похожих символов (0/O, 1/l/I), чтобы его легко было продиктовать.
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PASSWORD_LENGTH = 10


def get_organizer_meetup(meetup_id):
    meetup = get_meetup(meetup_id)
    require_organizer(meetup.club_id)
    return meetup


def serialize_user(user):
    return {"id": user.id, "display_name": user.display_name, "login": user.login}


# Данные панели

def serialize_desk_attempts(series, count):
    attempts = [None] * count
    for attempt in series.attempts:
        item = serialize_attempt(attempt)
        if attempt.solution is not None:
            item["solution"] = attempt.solution
        attempts[attempt.attempt_number - 1] = item
    return attempts


def serialize_desk_event(meetup_event, participants, disqualified):
    """Дисциплина для таблицы ввода: строка на каждого подтверждённого участника.

    Строки по имени, а не по месту: иначе при вводе они прыгали бы под курсором.
    Место и отметки рекордов — у строк из таблицы дисциплины. Дисквалифицированные
    тоже в списке, чтобы организатор мог поправить их попытки, но без места.
    """
    count = ATTEMPTS_COUNT[meetup_event.format.value]
    ranked = {row["series"].user_id: row for row in event_table(meetup_event)}
    series_by_user = {s.user_id: s for s in meetup_event.series}
    users = {p.user_id: p.user for p in participants}
    # Серия могла остаться у человека, чью заявку потом не подтвердили.
    for series in meetup_event.series:
        users.setdefault(series.user_id, series.user)

    rows = []
    for user in sorted(users.values(), key=lambda u: u.display_name):
        series = series_by_user.get(user.id)
        row = ranked.get(user.id)
        rows.append({
            "user": {"id": user.id, "display_name": user.display_name},
            "disqualified": user.id in disqualified,
            "place": row["place"] if row else None,
            "marks": row["marks"] if row else {"single": [], "average": []},
            "series": None if series is None else {
                "id": series.id,
                "version": series.version,
                "status": series.status.value,
                "attempts": serialize_desk_attempts(series, count),
                "best": series.best,
                "average": series.average,
            },
        })
    return {"event_id": meetup_event.event_id, "format": meetup_event.format.value, "rows": rows}


def approved_participants(meetup):
    return [p for p in meetup.participants if p.status == ParticipantStatus.APPROVED]


def disqualified_ids(meetup):
    return {d.user_id for d in meetup.disqualifications}


def desk_event(meetup, meetup_event):
    return serialize_desk_event(
        meetup_event, approved_participants(meetup), disqualified_ids(meetup),
    )


@desk.get("/meetups/<int:meetup_id>/desk")
def get_desk(meetup_id):
    """Всё для панели встречи: участники с дисквалификациями и таблицы дисциплин."""
    meetup = get_organizer_meetup(meetup_id)
    participants = approved_participants(meetup)
    disqualifications = {d.user_id: d for d in meetup.disqualifications}
    return {
        "participants": [
            {
                "user": serialize_user(p.user),
                "disqualification": serialize_disqualification(disqualifications.get(p.user_id)),
            }
            for p in sorted(participants, key=lambda p: p.user.display_name)
        ],
        "events": [
            serialize_desk_event(e, participants, set(disqualifications))
            for e in meetup.events
        ],
    }


# Ввод и правка попыток

def require_started(meetup):
    if meetup.status == MeetupStatus.PLANNED:
        raise ApiError(409, "meetup_not_started", "Встреча ещё не началась")


@desk.put(
    "/meetups/<int:meetup_id>/events/<event_id>/participants/<int:user_id>/attempts/<int:number>"
)
def put_attempt(meetup_id, event_id, user_id, number):
    """Ввод или правка попытки участника организатором.

    Можно поправить любую сохранённую попытку или добавить следующую по порядку.
    Нет серии — она создаётся с первой попыткой (version в запросе — null).
    Работает и после завершения встречи: ручная обработка бумажных бланков.
    """
    meetup = get_organizer_meetup(meetup_id)
    require_started(meetup)
    meetup_event = get_meetup_event(meetup, event_id)
    participant = db.session.get(MeetupParticipant, (meetup.id, user_id))
    if participant is None or participant.status != ParticipantStatus.APPROVED:
        raise ApiError(409, "not_approved", "Участник не подтверждён на встрече")

    data = json_body()
    version = data.get("version")
    fmc = is_fmc(event_id)
    if fmc:
        value, penalty = parse_value(data, FMC_PENALTIES, max_value=MAX_MOVES + 1)
        solution = parse_solution(data) if get_str(data, "solution") else None
    else:
        value, penalty = parse_value(data, TIME_PENALTIES)
        solution = None
    if version is not None and not is_int(version):
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")

    series = db.session.scalar(db.select(Series).where(
        Series.meetup_event_id == meetup_event.id, Series.user_id == user_id,
    ))
    try:
        if series is None:
            if version is not None:
                raise VersionConflict()
            series = Series(meetup_event=meetup_event, user_id=user_id)
            db.session.add(series)
            db.session.flush()
            version = series.version
        if not 1 <= number <= len(series.attempts) + 1:
            raise ApiError(
                409, "wrong_attempt_number", "Сначала введите предыдущие попытки",
                extra={"event": desk_event(meetup, meetup_event)},
            )
        save_attempt(series, number, value, penalty, version, current_user, solution=solution)
        db.session.commit()
    except (VersionConflict, StaleDataError, IntegrityError):
        # IntegrityError — серию за участника параллельно создал другой запрос.
        db.session.rollback()
        conflict = VersionConflict()
        conflict.extra = {"event": desk_event(meetup, meetup_event)}
        raise conflict
    return {"event": desk_event(meetup, meetup_event)}


@desk.delete(
    "/meetups/<int:meetup_id>/events/<event_id>/participants/<int:user_id>/attempts/<int:number>"
)
def remove_attempt(meetup_id, event_id, user_id, number):
    """Стирает ошибочно введённую попытку — только последнюю в серии.

    Серия без попыток удаляется. Тело запроса — {"version"} прочитанной серии.
    """
    meetup = get_organizer_meetup(meetup_id)
    meetup_event = get_meetup_event(meetup, event_id)
    version = json_body().get("version")
    if not is_int(version):
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")
    series = db.session.scalar(db.select(Series).where(
        Series.meetup_event_id == meetup_event.id, Series.user_id == user_id,
    ))

    try:
        if series is None:
            raise VersionConflict()
        delete_attempt(series, number, version)
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        conflict = VersionConflict()
        conflict.extra = {"event": desk_event(meetup, meetup_event)}
        raise conflict
    except ApiError as error:
        db.session.rollback()
        error.extra = {"event": desk_event(meetup, meetup_event)}
        raise
    return {"event": desk_event(meetup, meetup_event)}


def find_attempt(meetup_event, user_id, number):
    series = db.session.scalar(db.select(Series).where(
        Series.meetup_event_id == meetup_event.id, Series.user_id == user_id,
    ))
    attempts = series.attempts if series else []
    attempt = next((a for a in attempts if a.attempt_number == number), None)
    if attempt is None:
        raise ApiError(404, "not_found", "Попытка не найдена")
    return series, attempt


@desk.get(
    "/meetups/<int:meetup_id>/events/<event_id>/participants/<int:user_id>/attempts/<int:number>/history"
)
def attempt_history(meetup_id, event_id, user_id, number):
    """Журнал попытки: значения по порядку, кто и когда их установил. Первое — исходное."""
    meetup = get_organizer_meetup(meetup_id)
    _, attempt = find_attempt(get_meetup_event(meetup, event_id), user_id, number)
    return {"history": [
        {
            "value": entry.value,
            "penalty": entry.penalty.value,
            "solution": entry.solution,
            "changed_by": None if entry.user is None else {
                "id": entry.user.id, "display_name": entry.user.display_name,
            },
            "changed_at": iso_utc(entry.changed_at),
        }
        for entry in attempt.history
    ]}


@desk.post(
    "/meetups/<int:meetup_id>/events/<event_id>/participants/<int:user_id>/attempts/<int:number>/restore"
)
def restore_attempt(meetup_id, event_id, user_id, number):
    """Возвращает попытке исходный результат (первую запись журнала).

    Это обычная правка через save_attempt: она тоже попадает в журнал и
    пересчитывает рекорды. Тело запроса — {"version"} прочитанной серии.
    """
    meetup = get_organizer_meetup(meetup_id)
    meetup_event = get_meetup_event(meetup, event_id)
    version = json_body().get("version")
    if not is_int(version):
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")
    series, attempt = find_attempt(meetup_event, user_id, number)
    original = attempt.history[0]

    try:
        save_attempt(
            series, number, original.value, original.penalty, version, current_user,
            solution=original.solution,
        )
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        conflict = VersionConflict()
        conflict.extra = {"event": desk_event(meetup, meetup_event)}
        raise conflict
    return {"event": desk_event(meetup, meetup_event)}


# Участники

@desk.get("/meetups/<int:meetup_id>/candidates")
def list_candidates(meetup_id):
    """Участники клуба для ручного добавления на встречу, с поиском по имени и логину.

    Поиск — в Python: LOWER в SQLite не понимает кириллицу, а участников клуба немного.
    """
    meetup = get_organizer_meetup(meetup_id)
    query = request.args.get("q", "").strip().casefold()
    statuses = {p.user_id: p.status.value for p in meetup.participants}
    members = db.session.scalars(
        db.select(ClubMember).where(
            ClubMember.club_id == meetup.club_id, ClubMember.banned_at.is_(None),
        )
    ).all()
    found = [
        m.user for m in members
        if query in m.user.display_name.casefold() or query in m.user.login
    ]
    found.sort(key=lambda u: u.display_name)
    return {"candidates": [
        {"user": serialize_user(u), "status": statuses.get(u.id)} for u in found[:50]
    ]}


@desk.post("/meetups/<int:meetup_id>/participants")
def add_participant(meetup_id):
    """Добавляет участника сразу подтверждённым.

    {"user_id"} — участник клуба; {"display_name", "login"} — новый аккаунт
    с временным паролем. Пароль возвращается один раз и больше нигде не хранится.
    """
    meetup = get_organizer_meetup(meetup_id)
    data = json_body()
    password = None

    if "user_id" in data:
        user = db.session.get(User, data["user_id"]) if is_int(data["user_id"]) else None
        if user is None:
            raise ApiError(404, "not_found", "Пользователь не найден")
        if is_banned(meetup.club_id, user):
            raise ApiError(409, "banned", "Участник заблокирован в клубе")
    else:
        user, password = create_account(data)

    participant = db.session.get(MeetupParticipant, (meetup.id, user.id))
    if participant is None:
        participant = MeetupParticipant(meetup_id=meetup.id, user_id=user.id, user=user)
        db.session.add(participant)
    if participant.status != ParticipantStatus.APPROVED:
        approve(meetup, participant)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "conflict", "Участника уже добавили, обновите страницу")
    return {"user": serialize_user(user), "temporary_password": password}, 201


def create_account(data):
    display_name = collapse_spaces(get_str(data, "display_name"))
    login = normalize_login(get_str(data, "login"))
    raise_if_errors({"display_name": name_error(display_name), "login": login_error(login)})
    if db.session.scalar(db.select(User.id).where(User.login == login)):
        raise ValidationError({"login": "Логин уже занят"})

    password = "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH))
    user = User(
        login=login,
        display_name=display_name,
        password_hash=generate_password_hash(password),
        must_change_password=True,
        created_by=current_user.id,
    )
    db.session.add(user)
    db.session.flush()
    return user, password


# Дисквалификация

def serialize_disqualification(disqualification):
    if disqualification is None:
        return None
    return {"reason": disqualification.reason, "created_at": iso_utc(disqualification.created_at)}


def recalc_meetup_records(meetup):
    db.session.flush()
    for meetup_event in meetup.events:
        recalc_records(meetup.club_id, meetup_event.event_id)


@desk.put("/meetups/<int:meetup_id>/participants/<int:user_id>/disqualification")
def disqualify(meetup_id, user_id):
    """Дисквалификация на встрече: результаты участника уходят из таблиц и рекордов."""
    meetup = get_organizer_meetup(meetup_id)
    if db.session.get(MeetupParticipant, (meetup.id, user_id)) is None:
        raise ApiError(404, "not_found", "Участника нет на встрече")
    reason = collapse_spaces(get_str(json_body(), "reason"))
    raise_if_errors({
        "reason": "Укажите причину" if not reason else (
            f"Максимум {MAX_REASON_LENGTH} символов" if len(reason) > MAX_REASON_LENGTH else None
        ),
    })

    disqualification = find_disqualification(meetup, user_id)
    if disqualification is None:
        disqualification = Disqualification(
            meetup_id=meetup.id, user_id=user_id, created_by=current_user.id,
        )
        meetup.disqualifications.append(disqualification)
    disqualification.reason = reason
    recalc_meetup_records(meetup)
    db.session.commit()
    return {"disqualification": serialize_disqualification(disqualification)}


@desk.delete("/meetups/<int:meetup_id>/participants/<int:user_id>/disqualification")
def cancel_disqualification(meetup_id, user_id):
    meetup = get_organizer_meetup(meetup_id)
    disqualification = find_disqualification(meetup, user_id)
    if disqualification is not None:
        meetup.disqualifications.remove(disqualification)
        recalc_meetup_records(meetup)
        db.session.commit()
    return "", 204


def find_disqualification(meetup, user_id):
    return next((d for d in meetup.disqualifications if d.user_id == user_id), None)


# Завершение встречи

def unresolved_fmc(meetup):
    """Начатые, но не сданные попытки FMC: [(серия, попытка FMC)].

    Их нельзя просто сделать DNS — организатор разрешает их до завершения.
    """
    result = []
    for meetup_event in meetup.events:
        if not is_fmc(meetup_event.event_id):
            continue
        for series in meetup_event.series:
            saved = {a.attempt_number for a in series.attempts}
            result.extend(
                (series, f) for f in series.fmc_attempts if f.attempt_number not in saved
            )
    return result


def fmc_state(fmc_attempt, now):
    """frozen — сдача заморожена, expired — час вышел без сдачи, running — час идёт."""
    if fmc_attempt.frozen_at is not None:
        return "frozen", fmc_attempt.frozen_solution, fmc_attempt.frozen_at
    if now >= fmc_deadline(fmc_attempt):
        return "expired", fmc_attempt.draft, fmc_deadline(fmc_attempt)
    return "running", fmc_attempt.draft, now


def in_progress_series(meetup):
    return [
        s for e in meetup.events for s in e.series if s.status == SeriesStatus.IN_PROGRESS
    ]


@desk.get("/meetups/<int:meetup_id>/finish-summary")
def finish_summary(meetup_id):
    """Сводка для диалога завершения: незавершённые серии и неразрешённые попытки FMC."""
    meetup = get_organizer_meetup(meetup_id)
    now = utcnow()

    unfinished = {}
    dns_count = 0
    for series in in_progress_series(meetup):
        meetup_event = series.meetup_event
        count = ATTEMPTS_COUNT[meetup_event.format.value]
        dns_count += count - len(series.attempts)
        item = unfinished.setdefault(series.user_id, {
            "user": serialize_user(series.user), "events": [],
        })
        item["events"].append({
            "event_id": meetup_event.event_id,
            "attempts_done": len(series.attempts),
            "attempts_count": count,
        })

    fmc = []
    for series, fmc_attempt in unresolved_fmc(meetup):
        state, solution, _ = fmc_state(fmc_attempt, now)
        scramble = series.meetup_event.scrambles[fmc_attempt.attempt_number - 1]
        # Эти попытки не станут DNS: их разрешает организатор.
        dns_count -= 1
        fmc.append({
            "series_id": series.id,
            "version": series.version,
            "attempt_number": fmc_attempt.attempt_number,
            "user": serialize_user(series.user),
            "scramble": scramble.scramble,
            "solution": solution,
            "state": state,
            "deadline": iso_utc(fmc_deadline(fmc_attempt)),
        })

    return {
        "unfinished": sorted(unfinished.values(), key=lambda u: u["user"]["display_name"]),
        "dns_count": dns_count,
        "fmc": fmc,
    }


@desk.post("/meetups/<int:meetup_id>/fmc/<int:series_id>/<int:number>/resolve")
def resolve_fmc(meetup_id, series_id, number):
    """Результат неразрешённой попытки FMC, проверенной в браузере организатора.

    Решение — замороженный текст или, если час вышел без сдачи, последний черновик.
    Пока час идёт, можно поставить только DNF (текущий черновик сохраняется).
    """
    meetup = get_organizer_meetup(meetup_id)
    if meetup.status != MeetupStatus.LIVE:
        raise ApiError(409, "meetup_not_live", "Встреча сейчас не идёт")
    series = db.session.get(Series, series_id)
    if series is None or series.meetup_event.meetup_id != meetup.id:
        raise ApiError(404, "not_found", "Серия не найдена")
    fmc_attempt = next(
        (f for s, f in unresolved_fmc(meetup) if s.id == series.id and f.attempt_number == number),
        None,
    )
    if fmc_attempt is None:
        raise ApiError(409, "already_resolved", "Попытка уже сдана, данные обновлены")

    data = json_body()
    version = data.get("version")
    value, penalty = parse_value(data, {"none", "dnf"}, max_value=MAX_MOVES + 1)
    state, solution, submitted_at = fmc_state(fmc_attempt, utcnow())
    if state == "running" and penalty != Penalty.DNF:
        raise ApiError(409, "fmc_running", "Время попытки ещё идёт")
    if get_str(data, "solution") != (solution or ""):
        raise ApiError(409, "solution_changed", "Решение успело измениться, данные обновлены")
    if not is_int(version):
        raise ApiError(422, "invalid_attempt", "Некорректные данные попытки")

    try:
        save_attempt(
            series, number, value, penalty, version, current_user,
            solution=solution, submitted_at=submitted_at,
        )
        db.session.commit()
    except (VersionConflict, StaleDataError):
        db.session.rollback()
        raise VersionConflict()
    return "", 204


@desk.post("/meetups/<int:meetup_id>/finish")
def finish_meetup(meetup_id):
    """Завершение: несобранные попытки начатых серий становятся DNS, ссылка перестаёт работать.

    Неразрешённые попытки FMC должны быть разрешены до завершения.
    """
    meetup = get_organizer_meetup(meetup_id)
    if meetup.status != MeetupStatus.LIVE:
        raise ApiError(409, "meetup_not_live", "Завершить можно только идущую встречу")
    if unresolved_fmc(meetup):
        raise ApiError(409, "fmc_unresolved", "Сначала разрешите несданные попытки FMC")

    try:
        for series in in_progress_series(meetup):
            count = ATTEMPTS_COUNT[series.meetup_event.format.value]
            for number in range(len(series.attempts) + 1, count + 1):
                save_attempt(series, number, None, Penalty.DNS, series.version, current_user)
        meetup.status = MeetupStatus.FINISHED
        meetup.finished_at = utcnow()
        meetup.join_token = None
        db.session.commit()
    except (VersionConflict, StaleDataError):
        # Участник успел сдать попытку, пока шло завершение.
        db.session.rollback()
        raise ApiError(409, "version_conflict", "Кто-то успел сохранить попытку, попробуйте ещё раз")
    return {"meetup": serialize_meetup(meetup)}


# Скрамблы для печати

@desk.get("/meetups/<int:meetup_id>/scrambles")
def meetup_scrambles(meetup_id):
    """Скрамблы встречи для бланков. FMC не печатается: его скрамбл выдаётся после старта."""
    meetup = get_organizer_meetup(meetup_id)
    return {"events": [
        {
            "event_id": e.event_id,
            "format": e.format.value,
            "scrambles": [s.scramble for s in e.scrambles],
        }
        for e in meetup.events if not is_fmc(e.event_id)
    ]}
