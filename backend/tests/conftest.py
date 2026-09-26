import pytest

from app import create_app
from app.extensions import db

TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    # CSRF is checked by a separate test (test_auth.py) and disabled in the others.
    "WTF_CSRF_ENABLED": False,
}


@pytest.fixture
def app():
    return create_app(TEST_CONFIG)


@pytest.fixture
def client(app):
    # Create the schema and close the context right away: if it stayed open,
    # client requests would share one flask.g and Flask-Login would remember
    # the user between requests.
    with app.app_context():
        db.create_all()
    return app.test_client()


@pytest.fixture
def session(app):
    """DB session with an empty schema created from the models."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
