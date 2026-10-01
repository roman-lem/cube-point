"""Validation of login, registration and password change form fields.

Each function returns an error text or None.
"""

import re

from ..models import DELETED_USER_NAME

LOGIN_MIN, LOGIN_MAX = 3, 32
NAME_MIN, NAME_MAX = 2, 100
PASSWORD_MIN, PASSWORD_MAX = 8, 128

LOGIN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")
# Name or nickname: letters, digits, space and - ' ’ _ . (Анна-Мария, alex_cube, Д'Артаньян).
NAME_RE = re.compile(r"[\w .'’-]+")
LETTER_RE = re.compile(r"[^\W\d_]")
EMAIL_MAX = 254
# ASCII only: an address with other letters needs SMTPUTF8, which not every mail server has.
EMAIL_RE = re.compile(
    r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+"
)


def normalize_login(login):
    return login.strip().lower()


def normalize_email(email):
    # Lowercase: the same mailbox must not be bound to two accounts in different case.
    return email.strip().lower()


def email_error(email):
    if not email:
        return "Введите адрес почты"
    if len(email) > EMAIL_MAX or not EMAIL_RE.fullmatch(email):
        return "Проверьте адрес, например name@example.ru"
    return None


def login_error(login):
    if not login:
        return "Введите логин"
    if not LOGIN_MIN <= len(login) <= LOGIN_MAX:
        return f"От {LOGIN_MIN} до {LOGIN_MAX} символов"
    if not LOGIN_RE.fullmatch(login):
        return "Латинские буквы, цифры, «_», «.» и «-», начинается с буквы или цифры"
    return None


def name_error(name):
    if not name:
        return "Введите имя или никнейм"
    if not NAME_MIN <= len(name) <= NAME_MAX:
        return f"От {NAME_MIN} до {NAME_MAX} символов"
    if not NAME_RE.fullmatch(name):
        return "Буквы, цифры, пробел и символы - ' _ ."
    if not LETTER_RE.search(name):
        return "Нужна хотя бы одна буква"
    if _is_deleted_name(name):
        return "Это имя занято"
    return None


def _is_deleted_name(name):
    # Ignoring case and ё/е: a real participant must not look like a deleted one.
    def normalize(text):
        return text.casefold().replace("ё", "е")
    return normalize(name) == normalize(DELETED_USER_NAME)


def password_error(password):
    if not password:
        return "Введите пароль"
    if len(password) < PASSWORD_MIN:
        return f"Минимум {PASSWORD_MIN} символов"
    if len(password) > PASSWORD_MAX:
        return f"Максимум {PASSWORD_MAX} символов"
    return None
