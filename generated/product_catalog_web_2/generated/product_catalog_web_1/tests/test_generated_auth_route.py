from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from generated.services.api.app import app
from generated.services.api import auth as auth_mod


def test_login_issues_valid_jwt_and_get_current_user_accepts_it():
    client = TestClient(app)

    resp = client.post(
        "/v1/auth/login",
        json={"email": "u@example.com", "password": "secret"},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"

    token = data["access_token"]
    header_value = f"Bearer {token}"

    user = asyncio.run(auth_mod.get_current_user(authorization=header_value))

    assert user.id == "u@example.com"
    assert user.email == "u@example.com"
    assert user.roles == ["user"]
