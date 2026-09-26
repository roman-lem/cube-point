"""Parsing JSON requests and collecting field errors (format in errors.py)."""

from flask import request

from .errors import ValidationError


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def get_str(data, key):
    """String field from JSON; anything else counts as an empty string."""
    value = data.get(key)
    return value if isinstance(value, str) else ""


def is_int(value):
    # bool is a subclass of int in Python, so it is excluded explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def get_list(data, key):
    value = data.get(key)
    return value if isinstance(value, list) else []


def collapse_spaces(text):
    """Strips spaces at the edges and repeated spaces between words."""
    return " ".join(text.split())


def raise_if_errors(errors):
    errors = {field: message for field, message in errors.items() if message}
    if errors:
        raise ValidationError(errors)
