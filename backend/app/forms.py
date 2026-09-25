"""Разбор JSON-запросов и сбор ошибок полей (формат — в errors.py)."""

from flask import request

from .errors import ValidationError


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def get_str(data, key):
    """Строковое поле из JSON; всё остальное считается пустой строкой."""
    value = data.get(key)
    return value if isinstance(value, str) else ""


def is_int(value):
    # bool — подкласс int в Python, его отсекаем явно.
    return isinstance(value, int) and not isinstance(value, bool)


def get_list(data, key):
    value = data.get(key)
    return value if isinstance(value, list) else []


def collapse_spaces(text):
    """Убирает пробелы по краям и повторные пробелы между словами."""
    return " ".join(text.split())


def raise_if_errors(errors):
    errors = {field: message for field, message in errors.items() if message}
    if errors:
        raise ValidationError(errors)
