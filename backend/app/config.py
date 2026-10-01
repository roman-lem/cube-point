import os
from datetime import timedelta


class Config:
    """Settings from environment variables."""

    # Signs session cookies. Required outside tests: create_app refuses to start
    # without a long enough key (check_secret_key in __init__.py).
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    # A relative SQLite path is resolved against the instance/ folder.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///cubing.db")

    # Site address without a trailing slash: meetup links and QR codes are built
    # from it. In production it is https://<DOMAIN> (docker-compose.prod.yml).
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5173").rstrip("/")

    # Cookies over HTTPS only. Enabled by default in docker-compose,
    # disabled for local development with Vite.
    SECURE_COOKIES = os.environ.get("SECURE_COOKIES") == "1"

    # 0 closes registration: the form says registration opens soon and
    # the server rejects requests. Login and organizer-created accounts work.
    REGISTRATION_OPEN = os.environ.get("REGISTRATION_OPEN", "1") != "0"

    # Letters (mail.py) go through the mailbox on the site's domain, SMTP over SSL.
    # Without MAIL_HOST (development) a letter is not sent: only its subject is
    # written to the log, the whole letter only with MAIL_LOG_BODY=1 (links in it
    # carry tokens). docker-compose.prod.yml requires MAIL_HOST and never passes MAIL_LOG_BODY.
    # MAIL_FROM carries the sender name: "Name <noreply@example.ru>".
    MAIL_HOST = os.environ.get("MAIL_HOST", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "465"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "")
    # Seconds per SMTP operation: a stuck mail server must not hold the response.
    MAIL_TIMEOUT = 5
    MAIL_LOG_BODY = os.environ.get("MAIL_LOG_BODY") == "1"

    # Request body limit; Flask answers 413. The biggest real request
    # (a meetup with all events and scrambles) is far below it.
    MAX_CONTENT_LENGTH = 1024 * 1024

    # `flask seed` wipes and fills the database with demo data, so it only runs
    # where it is explicitly allowed (development), never on production by accident.
    ALLOW_SEED = os.environ.get("ALLOW_SEED") == "1"

    # The session lasts until the browser closes; "remember me" is the Flask-Login remember cookie.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = SECURE_COOKIES
    REMEMBER_COOKIE_DURATION = timedelta(days=180)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SECURE_COOKIES

    # The CSRF token is valid while the session lives. By default it expires
    # after an hour, and a long session would stop being able to submit forms.
    WTF_CSRF_TIME_LIMIT = None
