import pytest

from app import create_app
from app.extensions import db

TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    # CSRF проверяется отдельным тестом (test_auth.py), в остальных не мешает.
    "WTF_CSRF_ENABLED": False,
}


@pytest.fixture
def app():
    return create_app(TEST_CONFIG)


@pytest.fixture
def client(app):
    # Схему создаём и сразу закрываем контекст: если держать его открытым,
    # запросы клиента делили бы один flask.g, и Flask-Login запомнил бы
    # пользователя между запросами.
    with app.app_context():
        db.create_all()
    return app.test_client()


@pytest.fixture
def session(app):
    """Сессия БД с пустой схемой, созданной по моделям."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
