from flask import session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..errors import ApiError, ValidationError
from ..extensions import db
from ..forms import collapse_spaces, get_str, json_body, raise_if_errors
from ..models import User
from . import auth, throttle
from .validation import login_error, name_error, normalize_login, password_error

# Хеш, с которым сверяется пароль, если логина нет: так ответ приходит
# за то же время, и по нему нельзя понять, существует ли логин.
DUMMY_PASSWORD_HASH = generate_password_hash("dummy-password")


def serialize_user(user):
    return {
        "id": user.id,
        "login": user.login,
        "display_name": user.display_name,
        "email": user.email,
        "is_admin": user.is_admin,
        "must_change_password": user.must_change_password,
    }


def start_session(user, remember):
    login_user(user, remember=remember)
    # Запоминаем выбор, чтобы после смены пароля перевыпустить сессию так же.
    session["remember"] = remember


@auth.get("/csrf")
def csrf_token():
    return {"csrf_token": generate_csrf()}


@auth.get("/me")
def me():
    # Гость — не ошибка: фронт вызывает этот эндпоинт при каждом старте.
    user = serialize_user(current_user) if current_user.is_authenticated else None
    return {"user": user}


@auth.post("/register")
def register():
    data = json_body()
    display_name = collapse_spaces(get_str(data, "display_name"))
    login = normalize_login(get_str(data, "login"))
    password = get_str(data, "password")

    raise_if_errors({
        "display_name": name_error(display_name),
        "login": login_error(login),
        "password": password_error(password),
    })

    login_taken = ValidationError({"login": "Логин уже занят"})
    if db.session.scalar(db.select(User.id).where(User.login == login)):
        raise login_taken

    user = User(
        login=login,
        display_name=display_name,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Тот же логин успели зарегистрировать между проверкой и вставкой.
        db.session.rollback()
        raise login_taken

    # После регистрации сразу долгая сессия: чаще всего это телефон на встрече.
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

    wait = throttle.seconds_until_unblocked(login)
    if wait is not None:
        minutes = -(-wait // 60)  # вверх до целых минут
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
        throttle.record_failure(login)
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
    # Сам объект, а не прокси: он уйдёт в login_user.
    user = current_user._get_current_object()

    # При обязательной смене текущий пароль не спрашиваем:
    # человек только что вошёл по временному паролю.
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
    # Все остальные сессии и remember-куки перестают действовать.
    user.session_version += 1
    db.session.commit()

    start_session(user, remember=session.get("remember", False))
    return {"user": serialize_user(user)}
