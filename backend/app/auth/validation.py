"""Проверка полей форм входа, регистрации и смены пароля.

Каждая функция возвращает текст ошибки или None.
"""

import re

LOGIN_MIN, LOGIN_MAX = 3, 32
NAME_MIN, NAME_MAX = 3, 100
PASSWORD_MIN, PASSWORD_MAX = 8, 128

LOGIN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")
# Слово имени: буквы, внутри слова допустимы дефис и апостроф (Анна-Мария, Д'Артаньян).
NAME_WORD_RE = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")


def get_str(data, key):
    """Строковое поле из JSON; всё остальное считается пустой строкой."""
    value = data.get(key)
    return value if isinstance(value, str) else ""


def normalize_login(login):
    return login.strip().lower()


def normalize_name(name):
    # Лишние пробелы по краям и между словами убираем.
    return " ".join(name.split())


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
        return "Введите имя и фамилию"
    if not NAME_MIN <= len(name) <= NAME_MAX:
        return f"От {NAME_MIN} до {NAME_MAX} символов"
    words = name.split(" ")
    if not all(NAME_WORD_RE.fullmatch(word) for word in words):
        return "Только буквы, пробел, дефис и апостроф"
    if len(words) < 2:
        return "Укажите имя и фамилию"
    return None


def password_error(password):
    if not password:
        return "Введите пароль"
    if len(password) < PASSWORD_MIN:
        return f"Минимум {PASSWORD_MIN} символов"
    if len(password) > PASSWORD_MAX:
        return f"Максимум {PASSWORD_MAX} символов"
    return None
