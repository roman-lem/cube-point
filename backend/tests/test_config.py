import pytest

from app import create_app

from .conftest import TEST_CONFIG

GOOD_KEY = "k" * 32


@pytest.mark.parametrize("key", ["", "dev-secret-key", "k" * 31])
def test_app_refuses_weak_secret_key(key):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({**TEST_CONFIG, "TESTING": False, "SECRET_KEY": key})


def test_app_starts_with_long_secret_key():
    app = create_app({**TEST_CONFIG, "TESTING": False, "SECRET_KEY": GOOD_KEY})

    assert app.config["SECRET_KEY"] == GOOD_KEY


def test_request_body_is_limited_to_1_mb(client):
    response = client.post(
        "/api/auth/login", data=b"x" * (1024 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "payload_too_large"
