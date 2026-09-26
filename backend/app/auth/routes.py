from flask import current_app, request, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..accounts import delete_account, delete_restriction, publication_version
from ..consents import consent_errors, consents_required, record_consents
from ..errors import ApiError, ValidationError
from ..extensions import db
from ..forms import collapse_spaces, get_str, json_body, raise_if_errors
from ..models import ClubMember, Meetup, MeetupParticipant, ParticipantStatus, User
from . import auth, throttle
from .validation import login_error, name_error, normalize_login, password_error

# Hash to check the password against when the login does not exist: the response
# takes the same time, so it does not reveal whether the login exists.
DUMMY_PASSWORD_HASH = generate_password_hash("dummy-password")


def serialize_user(user):
    return {
        "id": user.id,
        "login": user.login,
        "display_name": user.display_name,
        "email": user.email,
        "is_admin": user.is_admin,
        "must_change_password": user.must_change_password,
        "consents_required": consents_required(user),
        # Why the account cannot be deleted (last organizer of a club), or None.
        "delete_restriction": delete_restriction(user),
    }


def start_session(user, remember):
    login_user(user, remember=remember)
    # Remember the choice to reissue the session the same way after a password change.
    session["remember"] = remember


@auth.get("/csrf")
def csrf_token():
    return {"csrf_token": generate_csrf()}


@auth.get("/me")
def me():
    # A guest is not an error: the frontend calls this endpoint on every start.
    user = serialize_user(current_user) if current_user.is_authenticated else None
    return {"user": user}


@auth.get("/home-club")
def home_club():
    """The club the site root leads a logged-in user to: the club of their latest meetup.

    Separate from /me because it changes while the app is open: an organizer
    approves the first request and the user joins the club.
    """
    if not current_user.is_authenticated:
        return {"club_id": None}
    # Only clubs the user is currently a member of.
    member_of = db.select(ClubMember.club_id).where(ClubMember.user_id == current_user.id)
    club_id = db.session.scalar(
        db.select(Meetup.club_id)
        .join(MeetupParticipant, MeetupParticipant.meetup_id == Meetup.id)
        .where(
            MeetupParticipant.user_id == current_user.id,
            MeetupParticipant.status == ParticipantStatus.APPROVED,
            Meetup.club_id.in_(member_of),
        )
        .order_by(Meetup.date.desc(), Meetup.starts_at.desc(), Meetup.id.desc())
        .limit(1)
    )
    if club_id is None:
        # No meetups yet (an organizer appointed by the administrator, or an account
        # created by an organizer): the club the user joined most recently.
        club_id = db.session.scalar(
            db.select(ClubMember.club_id)
            .where(ClubMember.user_id == current_user.id)
            .order_by(ClubMember.joined_at.desc(), ClubMember.club_id.desc())
            .limit(1)
        )
    return {"club_id": club_id}


@auth.get("/registration")
def registration_status():
    return {"open": current_app.config["REGISTRATION_OPEN"]}


@auth.post("/register")
def register():
    if not current_app.config["REGISTRATION_OPEN"]:
        raise ApiError(403, "registration_closed", "Регистрация скоро откроется")

    data = json_body()
    display_name = collapse_spaces(get_str(data, "display_name"))
    login = normalize_login(get_str(data, "login"))
    password = get_str(data, "password")

    raise_if_errors({
        "display_name": name_error(display_name),
        "login": login_error(login),
        "password": password_error(password),
        **consent_errors(data),
    })

    login_taken = ValidationError({"login": "Логин уже занят"})
    if db.session.scalar(db.select(User.id).where(User.login == login)):
        raise login_taken

    user = User(
        login=login,
        display_name=display_name,
        password_hash=generate_password_hash(password),
    )
    record_consents(user)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # The same login was registered between the check and the insert.
        db.session.rollback()
        raise login_taken

    # A long session right after registration: usually it is a phone at a meetup.
    start_session(user, remember=True)
    return {"user": serialize_user(user)}, 201


@auth.post("/login")
def login():
    data = json_body()
    login = normalize_login(get_str(data, "login"))[:64]
    password = get_str(data, "password")
    remember = data.get("remember") is True

    raise_if_errors({
        "login": None if login else "Введите логин",
        "password": None if password else "Введите пароль",
    })

    ip = request.remote_addr
    wait = throttle.seconds_until_unblocked(login, ip)
    if wait is not None:
        minutes = -(-wait // 60)  # round up to whole minutes
        raise ApiError(
            429, "too_many_attempts",
            f"Слишком много неудачных попыток. Попробуйте через {minutes} мин.",
            extra={"retry_after": wait},
            headers={"Retry-After": str(wait)},
        )

    user = db.session.scalar(db.select(User).where(User.login == login))
    password_ok = check_password_hash(
        user.password_hash if user else DUMMY_PASSWORD_HASH, password,
    )
    if user is None or not password_ok:
        throttle.record_failure(login, ip)
        raise ApiError(401, "invalid_credentials", "Неверный логин или пароль")

    throttle.clear_failures(login)
    start_session(user, remember)
    return {"user": serialize_user(user)}


@auth.post("/logout")
def logout():
    logout_user()
    session.pop("remember", None)
    return "", 204


@auth.post("/password")
@login_required
def change_password():
    data = json_body()
    current_password = get_str(data, "current_password")
    new_password = get_str(data, "new_password")
    # The object itself, not the proxy: it goes to login_user.
    user = current_user._get_current_object()

    # For a forced change the current password is not asked:
    # the user has just logged in with the temporary password.
    current_error = None
    if not user.must_change_password:
        if not current_password:
            current_error = "Введите текущий пароль"
        elif not check_password_hash(user.password_hash, current_password):
            current_error = "Неверный пароль"

    new_error = password_error(new_password)
    if not new_error and check_password_hash(user.password_hash, new_password):
        new_error = "Новый пароль совпадает с текущим"

    raise_if_errors({"current_password": current_error, "new_password": new_error})

    user.password_hash = generate_password_hash(new_password)
    user.must_change_password = False
    # All other sessions and remember cookies stop working.
    user.session_version += 1
    db.session.commit()

    start_session(user, remember=session.get("remember", False))
    return {"user": serialize_user(user)}


@auth.post("/consents")
@login_required
def accept_consents():
    """Consents from a user who has none (account created by an organizer)
    or whose consents became outdated after the text changed."""
    raise_if_errors(consent_errors(json_body()))
    record_consents(current_user)
    db.session.commit()
    return {"user": serialize_user(current_user)}


@auth.post("/delete-account")
@login_required
def delete_own_account():
    data = json_body()
    password = get_str(data, "password")
    # Keep the name in results and records: the publication consent
    # given earlier is not withdrawn (accounts.delete_account).
    keep_name = data.get("keep_name") is True
    user = current_user._get_current_object()

    if not password:
        raise ValidationError({"password": "Введите пароль"})
    if not check_password_hash(user.password_hash, password):
        raise ValidationError({"password": "Неверный пароль"})
    restriction = delete_restriction(user)
    if restriction:
        raise ApiError(409, "delete_restricted", restriction)
    if keep_name and publication_version(user) is None:
        raise ValidationError({"keep_name": "Вы не давали согласия на публикацию имени"})

    delete_account(user, keep_name=keep_name)
    db.session.commit()
    logout_user()
    session.pop("remember", None)
    return "", 204
