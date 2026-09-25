"""Участники клуба: публичный список и управление участниками. Адреса /api/clubs/<id>/members…

Список виден всем (без заблокированных). Карточка участника и действия —
организатору клуба и администратору. Правила — разделы «Роли»,
«Дисквалификация и блокировка» и «Авторизация» CLAUDE.md.
"""

from flask import Blueprint, request
from flask_login import current_user
from sqlalchemy import func

from .accounts import create_account, reset_password
from .auth import throttle
from .desk import parse_reason
from .errors import ApiError
from .extensions import db
from .forms import json_body
from .meetups import iso_utc
from .models import (
    Club, ClubMember, ClubRecord, ClubRole, Meetup, MeetupEvent, MeetupParticipant, MeetupStatus,
    ParticipantStatus, Series, User, utcnow,
)
from .permissions import get_or_404, is_last_organizer, is_organizer, require_club_manager
from .scoring import event_table

members = Blueprint("members", __name__)

FILTERS = ("all", "organizers", "banned")


def get_member(club_id, user_id):
    membership = db.session.get(ClubMember, (club_id, user_id))
    if membership is None:
        raise ApiError(404, "not_found", "Участник не найден")
    return membership


def can_manage(club_id):
    return current_user.is_authenticated and (current_user.is_admin or is_organizer(club_id))


def meetups_counts(club_id):
    """Число встреч клуба, где у человека есть хотя бы одна серия: {user_id: n}.

    Серии бывают только на начатых встречах, так что это и есть посещённые встречи.
    """
    return dict(db.session.execute(
        db.select(Series.user_id, func.count(func.distinct(MeetupEvent.meetup_id)))
        .join(MeetupEvent)
        .join(Meetup)
        .where(Meetup.club_id == club_id)
        .group_by(Series.user_id)
    ).all())


def records_counts(club_id):
    """Число текущих рекордов клуба (LR) у каждого: {user_id: n}."""
    return dict(db.session.execute(
        db.select(ClubRecord.user_id, func.count())
        .where(ClubRecord.club_id == club_id)
        .group_by(ClubRecord.user_id)
    ).all())


def serialize_ban(membership):
    if membership.banned_at is None:
        return None
    banned_by = db.session.get(User, membership.banned_by) if membership.banned_by else None
    return {
        "reason": membership.ban_reason,
        "banned_at": iso_utc(membership.banned_at),
        "banned_by": None if banned_by is None else {
            "id": banned_by.id, "display_name": banned_by.display_name,
        },
    }


# Список

@members.get("/clubs/<int:club_id>/members")
def list_members(club_id):
    """Участники клуба с поиском по имени (организатору — и по логину).

    Организатор и администратор видят и заблокированных, логины, фильтры и число
    людей в каждом фильтре. Остальным логин не отдаётся. Поиск — в Python: LOWER
    в SQLite не понимает кириллицу.
    """
    get_or_404(Club, club_id, "Клуб не найден")
    manager = can_manage(club_id)
    query = request.args.get("q", "").strip().casefold()
    selected = request.args.get("filter", "all")
    if selected not in FILTERS or not manager:
        selected = "all"

    memberships = db.session.scalars(
        db.select(ClubMember).where(ClubMember.club_id == club_id)
    ).all()
    if not manager:
        memberships = [m for m in memberships if m.banned_at is None]
    counts = meetups_counts(club_id)
    records = records_counts(club_id)

    def in_filter(membership, name):
        if name == "organizers":
            return membership.role == ClubRole.ORGANIZER
        if name == "banned":
            return membership.banned_at is not None
        return True

    found = [
        m for m in memberships
        if query in m.user.display_name.casefold() or (manager and query in m.user.login)
    ]

    def serialize(membership):
        user = {"id": membership.user.id, "display_name": membership.user.display_name}
        if manager:
            user["login"] = membership.user.login
        return {
            "user": user,
            "role": membership.role.value,
            "banned": membership.banned_at is not None,
            "meetups_count": counts.get(membership.user_id, 0),
            "records_count": records.get(membership.user_id, 0),
        }

    result = {
        "members": [
            serialize(m)
            for m in sorted(
                (m for m in found if in_filter(m, selected)),
                key=lambda m: m.user.display_name,
            )
        ],
        "can_manage": manager,
    }
    if manager:
        result["filter_counts"] = {
            name: sum(1 for m in found if in_filter(m, name)) for name in FILTERS
        }
    return result


@members.post("/clubs/<int:club_id>/members")
def create_member(club_id):
    """Новый аккаунт с временным паролем сразу в клубе (для новичка без телефона)."""
    club = get_or_404(Club, club_id, "Клуб не найден")
    require_club_manager(club.id)
    user, password = create_account(json_body())
    db.session.add(ClubMember(club_id=club.id, user_id=user.id))
    db.session.commit()
    return {
        "user": {"id": user.id, "display_name": user.display_name, "login": user.login},
        "temporary_password": password,
    }, 201


# Карточка участника

def restrictions(membership):
    """Почему действие недоступно: {действие: причина или None, если можно}.

    Эти же проверки выполняют эндпоинты действий, а фронт показывает причину
    у неактивной кнопки.
    """
    return {
        "reset_password": reset_password_restriction(membership.user),
        "organizer": organizer_restriction(membership),
        "ban": ban_restriction(membership),
    }


def reset_password_restriction(user):
    if user.id == current_user.id:
        return "Свой пароль меняется в профиле"
    if current_user.is_admin:
        return None
    if user.is_admin:
        return "Пароль администратора сбрасывает администратор"
    # Организатор любого клуба, а не только этого: иначе организатор одного клуба
    # мог бы войти под организатором другого.
    if db.session.scalar(db.select(ClubMember.user_id).where(
        ClubMember.user_id == user.id, ClubMember.role == ClubRole.ORGANIZER,
    ).limit(1)):
        return "Пароль организатора сбрасывает администратор"
    return None


def organizer_restriction(membership):
    if membership.role == ClubRole.ORGANIZER:
        if is_last_organizer(membership.club_id, membership.user_id):
            return "Нельзя снять последнего организатора"
        return None
    if membership.banned_at is not None:
        return "Сначала разблокируйте участника"
    return None


def ban_restriction(membership):
    if membership.banned_at is not None:
        return None  # разблокировать можно всегда
    if membership.user_id == current_user.id:
        return "Нельзя заблокировать самого себя"
    if membership.role == ClubRole.ORGANIZER:
        return "Сначала снимите права организатора"
    return None


def require_allowed(reason):
    if reason is not None:
        raise ApiError(409, "not_allowed", reason)


def member_meetups(membership):
    """Встречи клуба с сериями участника, от новых к старым, с его результатами."""
    rows = db.session.scalars(
        db.select(Series)
        .join(MeetupEvent)
        .join(Meetup)
        .where(Series.user_id == membership.user_id, Meetup.club_id == membership.club_id)
        .order_by(Meetup.date.desc(), Meetup.starts_at.desc(), MeetupEvent.id)
    ).all()

    meetups = {}
    for series in rows:
        meetup_event = series.meetup_event
        meetup = meetup_event.meetup
        if meetup.id not in meetups:
            disqualification = next(
                (d for d in meetup.disqualifications if d.user_id == series.user_id), None,
            )
            meetups[meetup.id] = {
                "id": meetup.id,
                "date": meetup.date.isoformat(),
                "place": meetup.place,
                "status": meetup.status.value,
                "disqualification": None if disqualification is None else {
                    "reason": disqualification.reason,
                    "created_at": iso_utc(disqualification.created_at),
                },
                "events": [],
            }
        # Место и отметки рекордов — из таблицы дисциплины. У дисквалифицированного их нет.
        row = next((r for r in event_table(meetup_event) if r["series"].id == series.id), None)
        meetups[meetup.id]["events"].append({
            "event_id": meetup_event.event_id,
            "format": meetup_event.format.value,
            "status": series.status.value,
            "best": series.best,
            "average": series.average,
            "place": row["place"] if row else None,
            "marks": row["marks"] if row else {"single": [], "average": []},
        })
    return list(meetups.values())


def live_meetup(membership):
    """Идущая встреча клуба, где участник подтверждён: блокировка прервёт его серии."""
    meetup = db.session.scalar(
        db.select(Meetup).join(MeetupParticipant).where(
            Meetup.club_id == membership.club_id,
            Meetup.status == MeetupStatus.LIVE,
            MeetupParticipant.user_id == membership.user_id,
            MeetupParticipant.status == ParticipantStatus.APPROVED,
        ).limit(1)
    )
    return None if meetup is None else {"id": meetup.id, "date": meetup.date.isoformat()}


def member_card(membership):
    user = membership.user
    meetups = member_meetups(membership)
    return {
        "user": {"id": user.id, "display_name": user.display_name, "login": user.login},
        "role": membership.role.value,
        "joined_at": iso_utc(membership.joined_at),
        "ban": serialize_ban(membership),
        "meetups_count": len(meetups),
        "meetups": meetups,
        "live_meetup": live_meetup(membership),
        "restrictions": restrictions(membership),
    }


def get_managed_member(club_id, user_id):
    get_or_404(Club, club_id, "Клуб не найден")
    require_club_manager(club_id)
    return get_member(club_id, user_id)


@members.get("/clubs/<int:club_id>/members/<int:user_id>")
def get_member_card(club_id, user_id):
    return {"member": member_card(get_managed_member(club_id, user_id))}


# Действия

@members.post("/clubs/<int:club_id>/members/<int:user_id>/password-reset")
def reset_member_password(club_id, user_id):
    """Временный пароль, показывается один раз. Все сессии участника завершаются."""
    membership = get_managed_member(club_id, user_id)
    require_allowed(reset_password_restriction(membership.user))
    password = reset_password(membership.user)
    # Если участника заблокировало ограничение попыток входа, новый пароль сразу работает.
    throttle.clear_failures(membership.user.login)
    db.session.commit()
    return {"temporary_password": password}


@members.put("/clubs/<int:club_id>/members/<int:user_id>/organizer")
def make_organizer(club_id, user_id):
    membership = get_managed_member(club_id, user_id)
    if membership.role != ClubRole.ORGANIZER:
        require_allowed(organizer_restriction(membership))
        membership.role = ClubRole.ORGANIZER
        db.session.commit()
    return {"member": member_card(membership)}


@members.delete("/clubs/<int:club_id>/members/<int:user_id>/organizer")
def remove_organizer(club_id, user_id):
    """Снимает права организатора; из клуба человек не удаляется. Снять можно и себя."""
    membership = get_managed_member(club_id, user_id)
    if membership.role == ClubRole.ORGANIZER:
        require_allowed(organizer_restriction(membership))
        membership.role = ClubRole.MEMBER
        db.session.commit()
    return {"member": member_card(membership)}


@members.put("/clubs/<int:club_id>/members/<int:user_id>/ban")
def ban_member(club_id, user_id):
    """Блокировка: нельзя подавать заявки и сдавать попытки, в том числе на идущей встрече.

    Уже сданные попытки, таблицы и рекорды не меняются. Повторный запрос меняет причину.
    """
    membership = get_managed_member(club_id, user_id)
    require_allowed(ban_restriction(membership))
    reason = parse_reason()
    if membership.banned_at is None:
        membership.banned_at = utcnow()
        membership.banned_by = current_user.id
    membership.ban_reason = reason
    db.session.commit()
    return {"member": member_card(membership)}


@members.delete("/clubs/<int:club_id>/members/<int:user_id>/ban")
def unban_member(club_id, user_id):
    membership = get_managed_member(club_id, user_id)
    membership.banned_at = None
    membership.banned_by = None
    membership.ban_reason = None
    db.session.commit()
    return {"member": member_card(membership)}
