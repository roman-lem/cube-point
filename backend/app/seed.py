"""Тестовые данные: `flask seed` (или `flask seed --reset`, чтобы очистить БД).

Клуб Tyumen | Speedcubing, две завершённые встречи и одна live.
Случайность с фиксированным зерном — данные каждый раз одинаковые
(кроме дат: они отсчитываются от сегодняшнего дня).
"""

import random
import secrets
from dataclasses import dataclass
from datetime import datetime, time, timedelta

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .events import EVENTS
from .extensions import db
from .models import (
    Attempt, Club, ClubLink, ClubMember, ClubRole, Disqualification, Format,
    LinkType, Meetup, MeetupEvent, MeetupParticipant, MeetupStatus,
    ParticipantStatus, Penalty, Scramble, Series, SeriesStatus, User, utcnow,
)
from .results import ATTEMPTS_COUNT, calc_series

PASSWORD = "password"
# Тюмень — UTC+5 круглый год (Asia/Yekaterinburg).
CLUB_UTC_OFFSET = timedelta(hours=5)


@dataclass
class Cuber:
    name: str
    login: str
    level: float  # среднее на 3×3 в секундах
    fmc: int | None = None  # среднее FMC в ходах, None — не решает FMC
    bld: float | None = None  # время 3BLD в секундах, None — не собирает вслепую
    no_phone: bool = False  # результаты за него вводит организатор
    user: User | None = None


ORGANIZER = Cuber("Алексей Смирнов", "a.smirnov", 11.5, fmc=32, bld=75)
REGULARS = [
    ORGANIZER,
    Cuber("Дмитрий Козлов", "d.kozlov", 9.2, fmc=29, bld=48),
    Cuber("Анна Волкова", "anna.volkova", 14.8, fmc=38),
    Cuber("Илья Морозов", "ilya.m", 12.3, bld=110),
    Cuber("Екатерина Новикова", "katya.n", 19.6, fmc=45),
    Cuber("Максим Лебедев", "max.lebedev", 16.1),
    Cuber("Софья Кузнецова", "sofia.k", 24.5),
    Cuber("Артём Соколов", "artem.sokolov", 10.7, fmc=35),
    Cuber("Мария Попова", "masha.popova", 31.0),
    Cuber("Никита Васильев", "nikita.v", 13.4, no_phone=True),
    Cuber("Полина Фёдорова", "polina.f", 21.8),
    Cuber("Егор Михайлов", "egor.m", 17.3),
]
EGOR = REGULARS[11]
# Новички подали заявку на текущую встречу, но ещё не в клубе.
PENDING = [
    Cuber("Иван Орлов", "ivan.orlov", 42.0),
    Cuber("Вероника Белова", "veronika.b", 27.5),
]
REJECTED = Cuber("Кирилл Зайцев", "kirill.z", 35.0)

# Во сколько раз время в дисциплине отличается от 3×3.
TIME_FACTORS = {"333": 1.0, "222": 0.42, "pyram": 0.38, "333oh": 1.8}
# Доля участников, которые сдают дисциплину (3×3 сдают все).
EVENT_POPULARITY = {"222": 0.75, "pyram": 0.5}


@click.command("seed")
@click.option("--reset", is_flag=True, help="Удалить все данные перед заполнением.")
@with_appcontext
def seed_command(reset):
    """Заполнить БД тестовыми данными."""
    if reset:
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
    elif db.session.query(User).first():
        raise click.ClickException("БД не пустая. Запустите `flask seed --reset`.")

    rng = random.Random(2026)
    now = utcnow().replace(second=0, microsecond=0)

    admin, organizer = _create_users(now)
    club = _create_club(now)

    first = _create_meetup(
        club, organizer, rng, now, days_ago=40, status=MeetupStatus.FINISHED,
        events=[("333", Format.AO5), ("222", Format.AO5), ("pyram", Format.AO5),
                ("333fm", Format.BO1)],
        attendees=REGULARS[:10],
    )
    second = _create_meetup(
        club, organizer, rng, now, days_ago=19, status=MeetupStatus.FINISHED,
        events=[("333", Format.AO5), ("333oh", Format.AO5), ("333bf", Format.BO5),
                ("222", Format.MO3)],
        attendees=REGULARS,
    )
    db.session.add(Disqualification(
        meetup_id=second.id, user_id=EGOR.user.id, created_by=organizer.id,
        reason="Результаты вводились без реальной сборки.",
        created_at=second.finished_at,
    ))
    live = _create_meetup(
        club, organizer, rng, now, days_ago=0, status=MeetupStatus.LIVE,
        events=[("333", Format.AO5), ("222", Format.AO5), ("333bf", Format.BO5)],
        attendees=[c for c in REGULARS if c.login not in ("katya.n", "polina.f")],
    )
    _add_join_requests(live, organizer, now)

    # Участники вступают в клуб при первом подтверждении заявки.
    for cuber in REGULARS:
        joined = first if cuber in REGULARS[:10] else second
        db.session.add(ClubMember(
            club_id=club.id, user_id=cuber.user.id, joined_at=joined.starts_at,
            role=ClubRole.ORGANIZER if cuber is ORGANIZER else ClubRole.MEMBER,
        ))

    db.session.commit()
    _print_summary(admin)


def _create_users(now):
    # Хеш считается медленно, у всех тестовых пользователей он один.
    password_hash = generate_password_hash(PASSWORD)
    admin = User(
        login="admin", display_name="Администратор", password_hash=password_hash,
        is_admin=True, created_at=now - timedelta(days=60),
    )
    db.session.add(admin)
    for cuber in REGULARS + PENDING + [REJECTED]:
        cuber.user = User(
            login=cuber.login, display_name=cuber.name, password_hash=password_hash,
            created_at=now - timedelta(days=50),
        )
        db.session.add(cuber.user)
    db.session.flush()

    # Аккаунт для пришедшего без телефона создал организатор.
    nikita = next(c for c in REGULARS if c.no_phone).user
    nikita.created_by = ORGANIZER.user.id
    nikita.must_change_password = True
    return admin, ORGANIZER.user


def _create_club(now):
    club = Club(
        name="Tyumen | Speedcubing", city="Тюмень", timezone="Asia/Yekaterinburg",
        description="Клуб спидкуберов Тюмени. Встречаемся по выходным, "
                    "собираем кубики и проводим мини-соревнования.",
        created_at=now - timedelta(days=55),
        links=[
            ClubLink(type=LinkType.VK, url="https://vk.com/tyumen_speedcubing", position=0),
        ],
    )
    db.session.add(club)
    db.session.flush()
    return club


def _create_meetup(club, organizer, rng, now, days_ago, status, events, attendees):
    if status == MeetupStatus.LIVE:
        starts_at = now - timedelta(hours=2)
    else:
        local_date = (now + CLUB_UTC_OFFSET).date() - timedelta(days=days_ago)
        starts_at = datetime.combine(local_date, time(12, 0)) - CLUB_UTC_OFFSET
    ends_at = starts_at + timedelta(hours=4)

    meetup = Meetup(
        club_id=club.id, date=(starts_at + CLUB_UTC_OFFSET).date(),
        starts_at=starts_at, ends_at=ends_at,
        place="Антикафе «Кубик»", address="ул. Республики, 10",
        status=status, created_by=organizer.id,
    )
    if status == MeetupStatus.FINISHED:
        meetup.finished_at = ends_at
    else:
        meetup.join_token = secrets.token_urlsafe(24)
    db.session.add(meetup)

    for cuber in attendees:
        meetup.participants.append(MeetupParticipant(
            user_id=cuber.user.id, status=ParticipantStatus.APPROVED,
            requested_at=starts_at - timedelta(minutes=rng.randint(5, 60)),
            decided_at=starts_at, decided_by=organizer.id,
        ))

    for event_id, series_format in events:
        meetup_event = MeetupEvent(event_id=event_id, format=series_format)
        meetup.events.append(meetup_event)
        scrambles = [
            _scramble(event_id, rng) for _ in range(ATTEMPTS_COUNT[series_format])
        ]
        meetup_event.scrambles = [
            Scramble(attempt_number=i, scramble=s) for i, s in enumerate(scrambles, 1)
        ]
        for cuber in attendees:
            if _takes_part(cuber, event_id, rng):
                _add_series(meetup, meetup_event, scrambles, cuber, organizer, rng)

    db.session.flush()
    return meetup


def _takes_part(cuber, event_id, rng):
    if event_id == "333fm":
        return cuber.fmc is not None
    if event_id == "333bf":
        return cuber.bld is not None
    if event_id == "333oh":
        return cuber.level < 18
    return rng.random() < EVENT_POPULARITY.get(event_id, 1.0)


def _add_series(meetup, meetup_event, scrambles, cuber, organizer, rng):
    count = len(scrambles)
    result_type = EVENTS[meetup_event.event_id].result_type
    is_live = meetup.status == MeetupStatus.LIVE

    if is_live:
        # На текущей встрече часть серий ещё не начата или не закончена.
        solved = rng.randint(0, count)
        if solved == 0:
            return
    elif count > 1 and rng.random() < 0.12:
        solved = rng.randint(1, count - 1)  # ушёл, не дособрав серию
    else:
        solved = count

    started_at = meetup.starts_at + timedelta(minutes=rng.randint(0, 60 if is_live else 150))
    series = Series(user_id=cuber.user.id, started_at=started_at)
    meetup_event.series.append(series)

    entered_by = organizer.id if cuber.no_phone else cuber.user.id
    submitted_at = started_at
    for number in range(1, solved + 1):
        if meetup_event.event_id == "333fm":
            submitted_at += timedelta(minutes=rng.randint(35, 60))
            value, penalty, solution = _fmc_attempt(cuber, scrambles[number - 1], rng)
        else:
            submitted_at += timedelta(seconds=rng.randint(90, 240))
            value, penalty = _timed_attempt(cuber, meetup_event.event_id, rng)
            solution = None
        series.attempts.append(Attempt(
            attempt_number=number, value=value, penalty=penalty, solution=solution,
            submitted_at=submitted_at, entered_by=entered_by,
        ))

    # При завершении встречи несобранные попытки начатых серий становятся DNS.
    if meetup.status == MeetupStatus.FINISHED:
        for number in range(solved + 1, count + 1):
            series.attempts.append(Attempt(
                attempt_number=number, value=None, penalty=Penalty.DNS,
                submitted_at=meetup.finished_at,
            ))

    if len(series.attempts) == count:
        series.status = SeriesStatus.COMPLETED
        series.completed_at = series.attempts[-1].submitted_at

    result = calc_series(
        [{"value": a.value, "penalty": a.penalty} for a in series.attempts],
        meetup_event.format, result_type,
    )
    series.best = result["best"]
    series.average = result["average"]


def _timed_attempt(cuber, event_id, rng):
    if event_id == "333bf":
        value = round(cuber.bld * 100 * max(0.7, rng.gauss(1, 0.15)))
        return value, Penalty.DNF if rng.random() < 0.35 else Penalty.NONE

    seconds = cuber.level * TIME_FACTORS[event_id] * max(0.75, rng.gauss(1, 0.09))
    roll = rng.random()
    if roll < 0.05:
        penalty = Penalty.PLUS2
    elif roll < 0.08:
        penalty = Penalty.DNF  # время остаётся, чтобы штраф можно было снять
    else:
        penalty = Penalty.NONE
    return round(seconds * 100), penalty


def _fmc_attempt(cuber, scramble, rng):
    """Решение, которое действительно собирает кубик.

    Берётся обратная последовательность к скрамблу и удлиняется до
    уровня участника вставками взаимно сокращающихся пар ходов.
    DNF — то же решение без одного хода, оно уже не собирает кубик.
    """
    moves = _inverse(scramble.split())
    extra = max(0, round(rng.gauss(cuber.fmc, 3)) - len(moves))
    if extra % 2:
        doubles = [i for i, m in enumerate(moves) if m.endswith("2")]
        if doubles:
            i = rng.choice(doubles)
            moves[i:i + 1] = [moves[i][0], moves[i][0]]  # R2 → R R
        extra -= 1
    for _ in range(extra // 2):
        face = rng.choice("RLUDFB")
        pos = rng.randint(0, len(moves))
        moves[pos:pos] = [face, face + "'"]

    if rng.random() < 0.1:
        del moves[rng.randrange(len(moves))]
        return None, Penalty.DNF, " ".join(moves)
    return len(moves), Penalty.NONE, " ".join(moves)


def _inverse(moves):
    inverted = {"": "'", "'": "", "2": "2"}
    return [m[0] + inverted[m[1:]] for m in reversed(moves)]


# Скрамблы — случайные ходы. Они не официальные и для тестовых данных
# этого достаточно; на реальных встречах их генерирует приложение.

CUBE_AXES = {"R": 0, "L": 0, "U": 1, "D": 1, "F": 2, "B": 2}


def _scramble(event_id, rng):
    if event_id == "222":
        return _random_moves("RUF", ["", "'", "2"], 10, rng)
    if event_id == "pyram":
        moves = _random_moves("RLUB", ["", "'"], 9, rng)
        tips = [t + rng.choice(["", "'"]) for t in "ulrb" if rng.random() < 0.5]
        return " ".join([moves] + tips)
    length = 22 if event_id == "333fm" else 20
    return _random_moves("RLUDFB", ["", "'", "2"], length, rng, CUBE_AXES)


def _random_moves(faces, suffixes, length, rng, axes=None):
    moves = []
    while len(moves) < length:
        face = rng.choice(faces)
        if moves and face == moves[-1][0]:
            continue
        # R L R — лишний ход: R и L на одной оси, третий ход сокращается.
        if axes and len(moves) >= 2 and axes[face] == axes[moves[-1][0]] == axes[moves[-2][0]]:
            continue
        moves.append(face + rng.choice(suffixes))
    return " ".join(moves)


def _add_join_requests(meetup, organizer, now):
    for cuber in PENDING:
        meetup.participants.append(MeetupParticipant(
            user_id=cuber.user.id, status=ParticipantStatus.PENDING,
            requested_at=now - timedelta(minutes=15),
        ))
    meetup.participants.append(MeetupParticipant(
        user_id=REJECTED.user.id, status=ParticipantStatus.REJECTED,
        requested_at=meetup.starts_at, decided_at=meetup.starts_at + timedelta(minutes=5),
        decided_by=organizer.id,
    ))


def _print_summary(admin):
    series = db.session.query(Series)
    attempts = db.session.query(Attempt)
    click.echo("Тестовые данные созданы.")
    click.echo(f"  Пароль у всех пользователей: {PASSWORD} (администратор: {admin.login})")
    click.echo(f"  Пользователей: {db.session.query(User).count()}, "
               f"встреч: {db.session.query(Meetup).count()}, "
               f"серий: {series.count()} "
               f"(незавершённых: {series.filter_by(status=SeriesStatus.IN_PROGRESS).count()})")
    click.echo(f"  Попыток: {attempts.count()}, "
               f"+2: {attempts.filter_by(penalty=Penalty.PLUS2).count()}, "
               f"DNF: {attempts.filter_by(penalty=Penalty.DNF).count()}, "
               f"DNS: {attempts.filter_by(penalty=Penalty.DNS).count()}")
