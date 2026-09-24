import os


class Config:
    """Настройки из переменных окружения."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    # Относительный путь SQLite считается от папки instance/.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///cubing.db")
