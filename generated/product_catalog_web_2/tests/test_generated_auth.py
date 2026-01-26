from __future__ import annotations

import asyncio

from generated.services.api import auth


def test_create_and_decode_access_token_roundtrip():
    token = auth.create_access_token({"sub": "user-1", "email": "u@example.com", "roles": ["user"]})
    assert isinstance(token, str)

    data = auth.decode_access_token(token)
    assert data["sub"] == "user-1"
    assert data["email"] == "u@example.com"
    assert data["roles"] == ["user"]
    assert "exp" in data
    assert "iat" in data


def test_get_current_user_from_bearer_header():
    token = auth.create_access_token(
        {"sub": "user-2", "email": "b@example.com", "roles": ["admin"]}
    )
    header_value = f"Bearer {token}"

    user = asyncio.run(auth.get_current_user(authorization=header_value))

    assert user.id == "user-2"
    assert str(user.email) == "b@example.com"
    assert user.roles == ["admin"]
