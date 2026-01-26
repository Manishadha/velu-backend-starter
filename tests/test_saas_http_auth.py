from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.app_server.saas_http import get_current_workspace, get_saas_registry  # noqa: F401
from services.app_server.saas_registry import InMemorySaasRegistry
from services.app_server.schemas.saas import ApiKey, Subscription, User, Workspace


TOKEN_PREFIX = "velu_123"

TOKEN = f"{TOKEN_PREFIX}.test"


def _demo_workspace() -> Workspace:
    return Workspace(
        id="ws_1",
        name="Demo Workspace",
        slug="demo_workspace",
        owner_user_id="user_1",
        plan="pro",
    )


def _demo_user() -> User:
    return User(
        id="user_1",
        email="user@example.com",
        name="User One",
        primary_workspace_id="ws_1",
        workspace_ids=["ws_1"],
    )


def _demo_api_key(prefix: str = TOKEN_PREFIX) -> ApiKey:
    return ApiKey(
        id="key_1",
        workspace_id="ws_1",
        name="Main Key",
        key_prefix=prefix,
        hashed_secret="hashed_value",
    )


def _demo_subscription_active() -> Subscription:
    return Subscription(
        id="sub_1",
        workspace_id="ws_1",
        plan="pro",
        status="active",
        seats=3,
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
    )


def _build_registry(active_workspace: bool = True) -> InMemorySaasRegistry:
    reg = InMemorySaasRegistry()

    ws = _demo_workspace()
    if not active_workspace:
        ws.is_active = False
    reg.add_workspace(ws)

    reg.add_user(_demo_user())
    reg.add_api_key(_demo_api_key())
    reg.add_subscription(_demo_subscription_active())

    return reg


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/whoami")
    async def whoami(ws: Workspace = Depends(get_current_workspace)):
        return {
            "workspace_id": ws.id,
            "workspace_slug": ws.slug,
            "plan": ws.plan,
        }

    return app


def test_saas_http_auth_with_authorization_header(monkeypatch) -> None:
    reg = _build_registry(active_workspace=True)

    def fake_get_registry():
        return reg

    monkeypatch.setattr(
        "services.app_server.saas_http.get_saas_registry",
        fake_get_registry,
    )

    app = _build_app()
    client = TestClient(app)

    resp = client.get("/whoami", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == "ws_1"
    assert data["workspace_slug"] == "demo_workspace"
    assert data["plan"] == "pro"


def test_saas_http_auth_missing_token(monkeypatch) -> None:
    reg = _build_registry(active_workspace=True)

    def fake_get_registry():
        return reg

    monkeypatch.setattr(
        "services.app_server.saas_http.get_saas_registry",
        fake_get_registry,
    )

    app = _build_app()
    client = TestClient(app)

    resp = client.get("/whoami")
    assert resp.status_code == 401

    assert resp.json()["detail"].lower().startswith("missing")


def test_saas_http_auth_inactive_workspace(monkeypatch) -> None:
    reg = _build_registry(active_workspace=False)

    def fake_get_registry():
        return reg

    monkeypatch.setattr(
        "services.app_server.saas_http.get_saas_registry",
        fake_get_registry,
    )

    app = _build_app()
    client = TestClient(app)

    resp = client.get("/whoami", headers={"X-API-Key": TOKEN})
    # Inactive workspace should be forbidden
    assert resp.status_code == 403
    assert "inactive" in resp.json()["detail"].lower()
