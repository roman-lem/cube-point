"""Проверка полей форм входа, регистрации и смены пароля.

Каждая функция возвращает текст ошибки или None.
"""

import re

from ..models import DELETED_USER_NAME

LOGIN_MIN, LOGIN_MAX = 3, 32
NAME_MIN, NAME_MAX = 2, 100
PASSWORD_MIN, PASSWORD_MAX = 8, 128

LOGIN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")
# Имя или никнейм: буквы, цифры, пробел и символы - ' ’ _ . (Анна-Мария, alex_cube, Д'Артаньян).
NAME_RE = re.compile(r"[\w .'’-]+")
LETTER_RE = re.compile(r"[^\W\d_]")


def normalize_login(login):
    return login.strip().lower()


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
    # Без учёта регистра и ё/е: живой участник не должен выглядеть удалённым.
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
