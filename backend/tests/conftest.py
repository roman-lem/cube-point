import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    return create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session(app):
    """Сессия БД с пустой схемой, созданной по моделям."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
