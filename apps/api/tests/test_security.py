import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)


def test_password_hash_verifies_without_exposing_plaintext():
    password = "a-long-test-password-123"
    encoded = hash_password(password)
    assert encoded != password
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)


def test_refresh_tokens_are_random_and_only_hashed_for_storage():
    token = new_refresh_token()
    assert len(token) > 40
    assert hash_token(token) != token
    assert hash_token(token) == hash_token(token)


def test_access_token_is_issued():
    token = create_access_token("user-id")
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    assert payload["sub"] == "user-id"
