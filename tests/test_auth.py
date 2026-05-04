from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from pymon import auth


def test_password_hashing_and_verification():
    password_hash = auth.hash_password("secure_password_123")

    assert isinstance(password_hash, str)
    assert password_hash != "secure_password_123"
    assert auth.verify_password("secure_password_123", password_hash) is True
    assert auth.verify_password("wrong_password", password_hash) is False


def test_create_and_decode_token():
    token = auth.create_token(user_id=1, username="admin", is_admin=True, must_change=False)

    payload = auth.decode_token(token)

    assert payload["sub"] == "admin"
    assert payload["user_id"] == 1
    assert payload["is_admin"] is True
    assert payload["must_change_password"] is False


def test_decode_token_rejects_invalid_signature():
    token = jwt.encode(
        {
            "sub": "admin",
            "user_id": 1,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "wrong-secret",
        algorithm=auth.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        auth.decode_token(token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_decode_token_rejects_expired_token():
    token = jwt.encode(
        {
            "sub": "admin",
            "user_id": 1,
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        auth.JWT_SECRET,
        algorithm=auth.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        auth.decode_token(token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired"
