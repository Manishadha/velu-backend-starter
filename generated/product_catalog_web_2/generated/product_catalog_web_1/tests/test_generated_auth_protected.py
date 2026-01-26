from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app


def test_me_requires_token():
    client = TestClient(app)
    resp = client.get("/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_me_with_valid_token_returns_user_info():
    client = TestClient(app)

    login_resp = client.post(
        "/v1/auth/login",
        json={"email": "me@example.com", "password": "secret"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200

    data = me_resp.json()
    assert data["id"] == "me@example.com"
    assert data["email"] == "me@example.com"
    assert data["roles"] == ["user"]
