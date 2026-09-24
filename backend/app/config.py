import os
from datetime import timedelta


class Config:
    """Настройки из переменных окружения."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    # Относительный путь SQLite считается от папки instance/.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///cubing.db")

    # Куки только по HTTPS. В docker-compose включено по умолчанию,
    # для локальной разработки через Vite выключено.
    SECURE_COOKIES = os.environ.get("SECURE_COOKIES") == "1"

    # Сессия живёт до закрытия браузера, «Запомнить меня» — remember-кука Flask-Login.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = SECURE_COOKIES
    REMEMBER_COOKIE_DURATION = timedelta(days=180)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SECURE_COOKIES

    # CSRF-токен действует, пока жива сессия. По умолчанию он истекает
    # через час, и долгая сессия перестала бы отправлять формы.
    WTF_CSRF_TIME_LIMIT = None
