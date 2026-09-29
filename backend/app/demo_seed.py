"""Demo data for showing the service: `flask seed-demo` (`--reset` wipes the DB first).

Unlike `flask seed` (edge cases for development) this is an ordinary club life:
three clubs with finished meetups, the main club also has a live meetup with
unfinished series. The demo member is in all three clubs. Password for everyone: PASSWORD.
Randomness with a fixed seed: the data is the same every time
(except dates, which are counted from today).
"""

import math
import random
import secrets
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .consents import record_consents
from .events import EVENTS
from .extensions import db
from .models import (
    Attempt, Club, ClubLink, ClubMember, ClubRole, LinkType, Meetup, MeetupEvent,
    MeetupParticipant, MeetupStatus, OrganizerPledge, ParticipantStatus, Penalty,
    Scramble, Series, SeriesStatus, User, utcnow,
)
from .pledge import PLEDGE_VERSION
from .results import ATTEMPTS_COUNT, calc_series
from .scoring import recalc_records
from .seed import CUBE_AXES, _attempt, _fmc_attempt, _random_moves, prepare_db

PASSWORD = "demo2026"

# How many times an event's time differs from 3x3.
TIME_FACTORS = {
    "333": 1.0, "222": 0.42, "444": 3.5, "555": 6.8, "333oh": 1.8,
    "minx": 8.5, "pyram": 0.42, "skewb": 0.48,
}
# Season length in days: at its start participants were slower by `improvement`.
SEASON_DAYS = 160


@dataclass
class Person:
    name: str
    login: str
    level: float  # current 3x3 average in seconds
    events: set
    fmc: int | None = None  # FMC mean in moves
    bld: float | None = None  # current 3BLD time in seconds
    improvement: float = 0.15  # how much slower they were at the start of the season
    user: User | None = None

    def level_at(self, days_ago):
        return self.level * (1 + self.improvement * days_ago / SEASON_DAYS)


ORGANIZER = Person(
    "Алексей Смирнов", "a.smirnov", 11.5, fmc=32, improvement=0.12,
    events={"333", "222", "444", "pyram", "skewb", "333fm"},
)
MEMBER = Person(
    "Дмитрий Козлов", "d.kozlov", 8.4, fmc=27, bld=45, improvement=0.18,
    events={"333", "222", "444", "555", "333oh", "pyram", "333bf", "333fm"},
)

CLUBS = [
    dict(
        name="Кубоград", city="Тюмень", timezone="Asia/Yekaterinburg", utc_offset=5,
        color="teal", vk="https://vk.com/kubograd",
        description="Клуб спидкуберов Тюмени. Встречаемся раз в две недели по воскресеньям: "
                    "собираем кубики, проводим мини-соревнования и помогаем новичкам "
                    "освоить первые алгоритмы.",
        place="Коворкинг «Точка»", address="ул. Республики, 42",
        members=50, extra_organizers=1, meetups=10, every_days=14, last_days_ago=7,
        live=True, member_meetups=None, organizer=ORGANIZER,
        events={"222": 0.9, "444": 0.6, "pyram": 0.6, "333oh": 0.5, "skewb": 0.35,
                "555": 0.3, "minx": 0.2, "333bf": 0.35, "333fm": 0.3},
    ),
    dict(
        name="Уральский кубик", city="Екатеринбург", timezone="Asia/Yekaterinburg",
        utc_offset=5, color="orange", vk="https://vk.com/ural_cube",
        description="Встречи спидкуберов Екатеринбурга. Раз в три недели по субботам, "
                    "всегда 3x3 и ещё несколько дисциплин на выбор.",
        place="Библиотека им. Белинского", address="ул. Белинского, 15",
        members=35, extra_organizers=2, meetups=7, every_days=21, last_days_ago=1,
        live=False, member_meetups=[2, 5], organizer=None,
        events={"222": 0.8, "444": 0.5, "pyram": 0.5, "333oh": 0.6, "skewb": 0.4,
                "555": 0.25, "333bf": 0.3},
    ),
    dict(
        name="Омская грань", city="Омск", timezone="Asia/Omsk", utc_offset=6,
        color="rose", vk="https://vk.com/omsk_gran",
        description="Небольшой, но дружный клуб любителей головоломок в Омске. "
                    "Собираемся раз в месяц.",
        place="Молодёжный центр «Квант»", address="пр. Мира, 20",
        members=30, extra_organizers=1, meetups=6, every_days=28, last_days_ago=15,
        live=False, member_meetups=[3], organizer=None,
        events={"222": 0.9, "pyram": 0.7, "skewb": 0.5, "444": 0.4, "333oh": 0.3,
                "minx": 0.2, "333fm": 0.25},
    ),
]

# Events at the live meetup of the main club.
LIVE_EVENTS = ["333", "222", "444", "pyram"]


@dataclass
class MeetupPlan:
    starts_at: datetime
    days_ago: int
    status: MeetupStatus
    attendees: list = field(default_factory=list)


@click.command("seed-demo")
@click.option("--reset", is_flag=True, help="Delete all data before seeding.")
@with_appcontext
def seed_demo_command(reset):
    """Fill the DB with demo data for showing the service."""
    prepare_db(reset, "seed-demo")

    rng = random.Random(2026)
    now = utcnow().replace(second=0, microsecond=0)
    names = NamePool()
    plans = [_plan_club(config, rng, now, names) for config in CLUBS]
    admin = _create_users(plans, now)
    for config, (people, organizers, meetups) in zip(CLUBS, plans):
        _create_club(config, people, organizers, meetups, rng, now)
    db.session.commit()
    _print_summary(admin)


# --- Plan: who is in which club and comes to which meetup ---

def _plan_club(config, rng, now, names):
    offset = timedelta(hours=config["utc_offset"])
    meetups = []
    for i in reversed(range(config["meetups"])):
        days_ago = config["last_days_ago"] + i * config["every_days"]
        local_date = (now + offset).date() - timedelta(days=days_ago)
        starts_at = datetime.combine(local_date, time(12, 0)) - offset
        meetups.append(MeetupPlan(starts_at, days_ago, MeetupStatus.FINISHED))
    finished = list(meetups)
    if config["live"]:
        started = now.replace(minute=0) - timedelta(hours=2)
        meetups.append(MeetupPlan(started, 0, MeetupStatus.LIVE))

    organizers = [config["organizer"]] if config["organizer"] else []
    organizers += [names.person(rng) for _ in range(config["extra_organizers"])]
    people = organizers + [MEMBER]
    people += [names.person(rng) for _ in range(config["members"] - len(people))]

    for person in people:
        if person in organizers:
            visits = [m for m in finished if rng.random() < 0.95]
        elif person is MEMBER and config["member_meetups"] is not None:
            visits = [finished[i] for i in config["member_meetups"]]
        else:
            # Some people joined the club in the middle of the season.
            start = 0 if rng.random() < 0.65 else rng.randrange(1, len(finished))
            chance = 0.9 if person is MEMBER else rng.uniform(0.3, 0.85)
            visits = [m for m in finished[start:] if rng.random() < chance]
            if not visits:
                visits = [rng.choice(finished[start:])]
        for meetup in visits:
            meetup.attendees.append(person)

    if config["live"]:
        live = meetups[-1]
        live.attendees = [
            p for p in people
            if p in organizers or p is MEMBER or rng.random() < 0.4
        ]
    return people, organizers, meetups


class NamePool:
    """Unique Russian names with logins like a.ivanov."""

    MALE = [
        "Алексей", "Дмитрий", "Иван", "Максим", "Артём", "Никита", "Егор", "Илья",
        "Кирилл", "Михаил", "Андрей", "Сергей", "Павел", "Роман", "Тимофей", "Матвей",
        "Даниил", "Глеб", "Лев", "Фёдор", "Георгий", "Степан", "Ярослав", "Марк",
        "Владимир", "Константин", "Денис", "Антон", "Олег", "Евгений",
    ]
    FEMALE = [
        "Анна", "Мария", "Екатерина", "Софья", "Полина", "Дарья", "Алиса", "Виктория",
        "Ксения", "Елизавета", "Варвара", "Вероника", "Ольга", "Татьяна", "Юлия",
        "Алёна", "Ульяна", "Кристина", "Милана", "Арина",
    ]
    SURNAMES = [
        "Иванов", "Петров", "Соколов", "Попов", "Лебедев", "Новиков", "Морозов",
        "Волков", "Соловьёв", "Васильев", "Зайцев", "Павлов", "Семёнов", "Голубев",
        "Виноградов", "Богданов", "Воробьёв", "Фёдоров", "Михайлов", "Беляев",
        "Тарасов", "Белов", "Комаров", "Орлов", "Киселёв", "Макаров", "Андреев",
        "Ковалёв", "Ильин", "Гусев", "Титов", "Кузьмин", "Кудрявцев", "Баранов",
        "Куликов", "Алексеев", "Степанов", "Яковлев", "Сорокин", "Сергеев",
        "Романов", "Захаров", "Борисов", "Королёв", "Герасимов", "Пономарёв",
        "Григорьев", "Лазарев", "Медведев", "Ершов", "Никитин", "Соболев", "Рябов",
        "Поляков", "Цветков", "Данилов", "Жуков", "Фролов", "Журавлёв", "Николаев",
        "Крылов", "Максимов", "Осипов", "Белоусов", "Егоров", "Матвеев", "Бобров",
        "Калинин", "Антонов", "Тимофеев", "Веселов", "Филиппов", "Марков", "Миронов",
        "Александров", "Коновалов", "Казаков", "Денисов", "Громов", "Фомин",
    ]
    TRANSLIT = dict(zip(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o",
         "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "sch", "", "y", "", "e",
         "yu", "ya"],
    ))

    def __init__(self):
        self.names = {ORGANIZER.name, MEMBER.name}
        self.logins = {ORGANIZER.login, MEMBER.login, "admin"}

    def person(self, rng):
        while True:
            surname = rng.choice(self.SURNAMES)
            if rng.random() < 0.6:
                first = rng.choice(self.MALE)
            else:
                first = rng.choice(self.FEMALE)
                surname += "а"
            name = f"{first} {surname}"
            if name not in self.names:
                break
        self.names.add(name)
        login = f"{self._latin(first)[0]}.{self._latin(surname)}"
        if login in self.logins:
            login = f"{self._latin(first)}.{self._latin(surname)}"
        self.logins.add(login)
        return _random_person(name, login, rng)

    def _latin(self, text):
        return "".join(self.TRANSLIT.get(c, c) for c in text.lower())


def _random_person(name, login, rng):
    level = round(min(45, max(9.5, rng.lognormvariate(math.log(18), 0.35))), 1)
    events = {"333"}
    chances = {"222": 0.85, "pyram": 0.6, "skewb": 0.4}
    if level < 30:
        chances["444"] = 0.7
    if level < 20:
        chances |= {"555": 0.55, "333oh": 0.65}
    if level < 18:
        chances["minx"] = 0.35
    events |= {e for e, chance in chances.items() if rng.random() < chance}
    person = Person(name, login, level, events, improvement=rng.uniform(0.05, 0.25))
    if level < 16 and rng.random() < 0.4:
        person.bld = round(level * rng.uniform(4.5, 8), 1)
        events.add("333bf")
    if rng.random() < 0.25:
        person.fmc = round(rng.uniform(28, 48))
        events.add("333fm")
    return person


# --- Database ---

def _create_users(plans, now):
    # Hashing is slow, so all demo users share one hash.
    password_hash = generate_password_hash(PASSWORD)
    admin = User(
        login="admin", display_name="Администратор", password_hash=password_hash,
        is_admin=True, created_at=now - timedelta(days=SEASON_DAYS + 30),
    )
    users = [admin]

    first_visit = {}
    for people, _, meetups in plans:
        for meetup in meetups:
            for person in meetup.attendees:
                if person.login not in first_visit or meetup.starts_at < first_visit[person.login]:
                    first_visit[person.login] = meetup.starts_at
    people = {p.login: p for plan in plans for p in plan[0]}
    for login, person in people.items():
        person.user = User(
            login=login, display_name=person.name, password_hash=password_hash,
            created_at=first_visit[login] - timedelta(days=3, hours=_hours(login)),
        )
        users.append(person.user)

    for user in users:
        record_consents(user)
        for consent in user.consents:
            consent.accepted_at = user.created_at
    db.session.add_all(users)
    db.session.flush()
    return admin


def _hours(login):
    return sum(map(ord, login)) % 48  # registration times are not all the same


def _create_club(config, people, organizers, meetups, rng, now):
    offset = timedelta(hours=config["utc_offset"])
    club = Club(
        name=config["name"], city=config["city"], timezone=config["timezone"],
        description=config["description"], logo_color=config["color"],
        created_at=meetups[0].starts_at - timedelta(days=30),
        links=[ClubLink(type=LinkType.VK, url=config["vk"], position=0)],
    )
    db.session.add(club)
    db.session.flush()

    head = organizers[0].user
    for plan in meetups:
        _create_meetup(club, config, plan, offset, head, rng, now)

    # Participants join the club when their request is approved for the first time.
    for person in people:
        joined = min(m.starts_at for m in meetups if person in m.attendees)
        is_organizer = person in organizers
        db.session.add(ClubMember(
            club_id=club.id, user_id=person.user.id, joined_at=joined,
            role=ClubRole.ORGANIZER if is_organizer else ClubRole.MEMBER,
        ))
        if is_organizer:
            db.session.add(OrganizerPledge(
                club_id=club.id, user_id=person.user.id, version=PLEDGE_VERSION,
                accepted_at=min(now, joined + timedelta(days=1)),
            ))

    db.session.flush()
    for event_id in EVENTS:
        recalc_records(club.id, event_id)


def _create_meetup(club, config, plan, offset, head, rng, now):
    is_live = plan.status == MeetupStatus.LIVE
    meetup = Meetup(
        club_id=club.id, date=(plan.starts_at + offset).date(),
        starts_at=plan.starts_at, ends_at=plan.starts_at + timedelta(hours=4),
        place=config["place"], address=config["address"],
        status=plan.status, created_by=head.id,
    )
    if is_live:
        meetup.join_token = secrets.token_urlsafe(24)
    else:
        meetup.finished_at = meetup.ends_at
    db.session.add(meetup)

    for person in plan.attendees:
        meetup.participants.append(MeetupParticipant(
            user_id=person.user.id, status=ParticipantStatus.APPROVED,
            requested_at=plan.starts_at - timedelta(minutes=rng.randint(5, 60)),
            decided_at=plan.starts_at, decided_by=head.id,
        ))

    if is_live:
        event_ids = LIVE_EVENTS
    else:
        event_ids = ["333"] + [e for e, chance in config["events"].items() if rng.random() < chance]
    for event_id in event_ids:
        series_format = EVENTS[event_id].default_format
        meetup_event = MeetupEvent(event_id=event_id, format=series_format)
        meetup.events.append(meetup_event)
        scrambles = [_scramble(event_id, rng) for _ in range(ATTEMPTS_COUNT[series_format])]
        meetup_event.scrambles = [
            Scramble(attempt_number=i, scramble=s) for i, s in enumerate(scrambles, 1)
        ]
        for person in plan.attendees:
            solved = _solved_count(person, event_id, len(scrambles), is_live, rng)
            if solved:
                _add_series(meetup_event, scrambles, person, solved, plan, rng)

    db.session.flush()


def _solved_count(person, event_id, count, is_live, rng):
    """How many attempts the person has submitted in the event, 0: no series."""
    if event_id not in person.events:
        return 0
    if not is_live:
        return count if event_id == "333" or rng.random() < 0.9 else 0
    # At the live meetup the demo accounts have a finished series, an unfinished one
    # and an event not started yet.
    if person is MEMBER:
        return {"333": count, "222": 2}.get(event_id, 0)
    if person is ORGANIZER:
        return {"333": 3}.get(event_id, 0)
    return rng.randint(0, count) if rng.random() < 0.8 else 0


def _add_series(meetup_event, scrambles, person, solved, plan, rng):
    event_id = meetup_event.event_id
    count = len(scrambles)
    is_fmc = event_id == "333fm"
    latest_start = 60 if plan.status == MeetupStatus.LIVE else 150
    started_at = plan.starts_at + timedelta(minutes=rng.randint(0, latest_start))
    series = Series(user_id=person.user.id, started_at=started_at)
    meetup_event.series.append(series)

    level = person.level_at(plan.days_ago)
    submitted_at = started_at
    for number in range(1, solved + 1):
        if is_fmc:
            submitted_at += timedelta(minutes=rng.randint(35, 60))
            value, penalty, solution = _fmc_attempt(person, scrambles[number - 1], rng)
        else:
            submitted_at += timedelta(seconds=rng.randint(90, 240))
            value, penalty = _timed_attempt(person, event_id, level, rng)
            solution = None
        series.attempts.append(
            _attempt(number, value, penalty, solution, submitted_at, person.user.id)
        )

    if solved == count:
        series.status = SeriesStatus.COMPLETED
        series.completed_at = submitted_at
    result = calc_series(
        [{"value": a.value, "penalty": a.penalty} for a in series.attempts],
        meetup_event.format, EVENTS[event_id].result_type,
    )
    series.best = result["best"]
    series.average = result["average"]


def _timed_attempt(person, event_id, level, rng):
    if event_id == "333bf":
        seconds = person.bld * level / person.level * max(0.75, rng.gauss(1, 0.12))
        return round(seconds * 100), Penalty.DNF if rng.random() < 0.3 else Penalty.NONE

    seconds = level * TIME_FACTORS[event_id] * max(0.8, rng.gauss(1, 0.08))
    roll = rng.random()
    if roll < 0.04:
        penalty = Penalty.PLUS2
    elif roll < 0.06:
        penalty = Penalty.DNF
    else:
        penalty = Penalty.NONE
    return round(seconds * 100), penalty


# Scrambles are random moves: not official, and enough for demo data.

def _scramble(event_id, rng):
    if event_id == "222":
        return _random_moves("RUF", ["", "'", "2"], 10, rng)
    if event_id == "pyram":
        moves = _random_moves("RLUB", ["", "'"], 9, rng)
        tips = [t + rng.choice(["", "'"]) for t in "ulrb" if rng.random() < 0.5]
        return " ".join([moves] + tips)
    if event_id == "skewb":
        return _random_moves("RLUB", ["", "'"], 9, rng)
    if event_id == "444":
        return _big_cube(44, "RUF", rng)
    if event_id == "555":
        return _big_cube(60, "RLUDFB", rng)
    if event_id == "minx":
        lines = []
        for _ in range(7):
            turns = [f"{'RD'[i % 2]}{rng.choice(['++', '--'])}" for i in range(10)]
            lines.append(" ".join(turns + [rng.choice(["U", "U'"])]))
        return " ".join(lines)
    moves = _random_moves("RLUDFB", ["", "'", "2"], 22 if event_id == "333fm" else 20,
                          rng, CUBE_AXES)
    if event_id == "333bf":
        # Blindfolded scrambles end with a random orientation.
        turn = rng.choice(["Rw", "Rw'", "Rw2", "Fw", "Fw'"]) + " " + rng.choice(["Uw", "Uw'", "Uw2"])
        moves += " " + turn
    return moves


def _big_cube(length, wide_faces, rng):
    moves = []
    while len(moves) < length:
        face = rng.choice("RLUDFB")
        if moves and moves[-1][0] == face:
            continue
        wide = "w" if face in wide_faces and rng.random() < 0.4 else ""
        moves.append(face + wide + rng.choice(["", "'", "2"]))
    return " ".join(moves)


def _print_summary(admin):
    series = db.session.query(Series)
    click.echo("Demo data created.")
    for club in db.session.query(Club).order_by(Club.id):
        members = db.session.query(ClubMember).filter_by(club_id=club.id).count()
        meetups = db.session.query(Meetup).filter_by(club_id=club.id).count()
        click.echo(f"  {club.name} ({club.city}): members {members}, meetups {meetups}")
    click.echo(f"  Series: {series.count()} "
          f"(unfinished: {series.filter_by(status=SeriesStatus.IN_PROGRESS).count()}), "
          f"attempts: {db.session.query(Attempt).count()}")
    click.echo(f"  Password for everyone: {PASSWORD}")
    click.echo(f"  Organizer of {CLUBS[0]['name']}: {ORGANIZER.login}")
    click.echo(f"  Member of all clubs: {MEMBER.login}")
    click.echo(f"  Administrator: {admin.login}")

