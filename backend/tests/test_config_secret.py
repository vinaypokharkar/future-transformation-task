"""The JWT secret validator.

A weak signing key is not a degraded state, it is a total authentication
bypass: anyone who knows the key mints admin tokens at will. These tests exist
because the previous default ("change-me") booted fine and passed every other
test in the suite — the failure was invisible from the inside.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings

VALID = "a" * 40


def _settings(secret):
    # _env_file=None so a developer's real .env cannot mask what is under test.
    return Settings(jwt_secret_key=secret, _env_file=None)


def test_accepts_a_strong_secret():
    assert _settings(VALID).jwt_secret_key == VALID


@pytest.mark.parametrize(
    "placeholder",
    [
        "change-me",
        "change-me-in-production-use-a-real-random-secret",  # the .env.example value
        "docker-demo-secret-not-for-production",
        "secret",
        "CHANGE-ME",  # case must not be an escape hatch
    ],
)
def test_rejects_known_placeholders(placeholder):
    """Including the one in .env.example.

    Copying .env.example is step one of the README, so this is the exact value a
    reviewer following the documented happy path would end up with.
    """
    with pytest.raises(PydanticValidationError) as exc:
        _settings(placeholder)
    assert "placeholder" in str(exc.value).lower()


@pytest.mark.parametrize("short", ["", "abc", "a" * 31])
def test_rejects_short_secrets(short):
    with pytest.raises(PydanticValidationError):
        _settings(short)


def test_secret_is_required(monkeypatch):
    """No default. Missing config must stop the process, not downgrade it.

    The env var has to be cleared explicitly: pydantic-settings reads the
    environment regardless of _env_file, and conftest sets JWT_SECRET_KEY for
    the rest of the suite — so without this the "missing" case is never
    actually missing.
    """
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(PydanticValidationError) as exc:
        Settings(_env_file=None)
    assert "jwt_secret_key" in str(exc.value).lower()


def test_error_message_tells_you_how_to_fix_it():
    """An error that does not say what to do just gets worked around."""
    with pytest.raises(PydanticValidationError) as exc:
        _settings("change-me")
    message = str(exc.value)
    assert "secrets.token_urlsafe" in message
    assert "JWT_SECRET_KEY" in message
