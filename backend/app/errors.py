"""Uniform API error format.

    {"error": {"code": "validation_error", "message": "...", "fields": {"login": "..."}}}

code is a machine-readable name for the client, message is the text to show,
fields are errors under form fields (validation_error only).
"""

from flask import jsonify
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None, extra=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields
        self.extra = extra or {}
        self.headers = headers or {}


class ValidationError(ApiError):
    def __init__(self, fields):
        super().__init__(422, "validation_error", "Проверьте поля формы", fields=fields)


def error_response(error):
    body = {"code": error.code, "message": error.message, **error.extra}
    if error.fields:
        body["fields"] = error.fields
    return jsonify(error=body), error.status, error.headers


# HTTP errors that Flask itself can return.
HTTP_ERRORS = {
    400: ("bad_request", "Некорректный запрос"),
    401: ("unauthorized", "Нужно войти"),
    403: ("forbidden", "Недостаточно прав"),
    404: ("not_found", "Не найдено"),
    405: ("method_not_allowed", "Метод не поддерживается"),
    500: ("internal_error", "Ошибка сервера, попробуйте ещё раз"),
}


def register_error_handlers(app):
    app.register_error_handler(ApiError, error_response)

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return error_response(ApiError(
            400, "csrf_failed", "Сессия устарела, обновите страницу",
        ))

    @app.errorhandler(HTTPException)
    def http_error(e):
        code, message = HTTP_ERRORS.get(e.code, ("http_error", e.name))
        return error_response(ApiError(e.code, code, message))
