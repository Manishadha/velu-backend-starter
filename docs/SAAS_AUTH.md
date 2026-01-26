# SaaS Auth & Workspaces

This document explains how Velu's SaaS layer models workspaces, API keys, and HTTP authentication.

It is based on:

- `services/app_server/schemas/saas.py`
- `services/app_server/saas_registry.py`
- `services/app_server/saas_auth.py`
- `services/app_server/saas_http.py`
- Tests:
  - `tests/test_saas_models.py`
  - `tests/test_saas_registry.py`
  - `tests/test_saas_auth.py`
  - `tests/test_saas_http_auth.py`

All behavior described here is covered by tests.

---

## 1. Core concepts

### 1.1 Workspace

A **workspace** is a tenant in the Velu SaaS world.

Model: `Workspace` (from `schemas.saas`), simplified:

- `id: str` – workspace ID.
- `slug: str` – URL-friendly identifier.
- `name: str` – display name.
- `owner_user_id: str` – ID of the owner user.
- `plan: PlanName` – e.g. `"free" | "pro" | "enterprise"`.
- `is_active: bool` – whether the workspace is active.

`InMemorySaasRegistry.workspace_is_active()` uses this plus subscriptions to decide if requests are allowed.

### 1.2 User

Model: `User` (from `schemas.saas`), simplified:

- `id: str`
- `email: str`
- `name: str`
- `is_active: bool`

Users are not deeply used by the HTTP auth layer yet, but they are part of the SaaS model.

### 1.3 API Key

Model: `ApiKey` (from `schemas.saas`), simplified:

- `id: str`
- `workspace_id: str`
- `key_prefix: str` – human-visible prefix used as the token.
- `is_active: bool`

The **“token”** used in headers is the `key_prefix`. In tests, keys look like:

```python
ApiKey(
    id="key_1",
    workspace_id="ws_1",
    key_prefix="velu_123",
    is_active=True,
)
1.4 Subscription

Model: Subscription (from schemas.saas), simplified:

id: str

workspace_id: str

plan: PlanName

status: Literal["trialing", "active", "past_due", "canceled", ...]

InMemorySaasRegistry.workspace_is_active() uses subscriptions plus Workspace.is_active to decide if a workspace is active.

2. In-memory SaaS registry
2.1 InMemorySaasRegistry

Implementation: services/app_server/saas_registry.py

This is a simple, test-friendly registry with methods:

add_workspace(ws: Workspace) -> None

add_user(user: User) -> None

add_api_key(key: ApiKey) -> None

add_subscription(sub: Subscription) -> None

get_workspace(workspace_id: str) -> Optional[Workspace]

get_user(user_id: str) -> Optional[User]

get_api_key_by_prefix(key_prefix: str) -> Optional[ApiKey]

list_api_keys_for_workspace(workspace_id: str) -> list[ApiKey]

get_subscription_for_workspace(workspace_id: str) -> Optional[Subscription]

workspace_plan(workspace_id: str) -> PlanName

workspace_is_active(workspace_id: str) -> bool

The workspace_is_active logic is:

If the workspace does not exist → False.

If workspace.is_active is False → False.

If there is no subscription → True.

If a subscription exists and status in ("active", "trialing") → True.

Otherwise → False.

2.2 Global registry accessor

Implementation: services/app_server/saas_http.py:

def get_saas_registry() -> InMemorySaasRegistry:
    # returns a singleton in-memory registry


Tests (test_saas_http_auth.py) monkeypatch this to inject a pre-seeded registry.

3. Header parsing and token resolution
3.1 Header formats

The SaaS auth layer accepts tokens in two forms:

Authorization header:

Authorization: Bearer <token>

Authorization: ApiKey <token>

X-API-Key header:

X-API-Key: <token>

Here, <token> is the API key prefix (e.g. "velu_123").

3.2 resolve_workspace_from_header

Implementation: services/app_server/saas_auth.py

Signature:

workspace, api_key, subscription, error = resolve_workspace_from_header(
    registry: InMemorySaasRegistry,
    raw_header: Optional[str],
)


Behavior (simplified and matched to tests):

Missing header:

When raw_header is None or empty:

returns (None, None, None, "missing_token")

Parse token:

If header starts with "Bearer " → token is the rest.

If header starts with "ApiKey " → token is the rest.

Otherwise, the header itself is treated as the token (for X-API-Key).

Lookup API key:

Calls registry.get_api_key_by_prefix(token).

If not found:

returns (None, None, None, "invalid_token").

Resolve workspace:

Use api_key.workspace_id to fetch the workspace via registry.get_workspace.

If no workspace:

returns (None, api_key, None, "invalid_token").

Check workspace active:

Uses registry.workspace_is_active(workspace.id).

If inactive:

returns (workspace, api_key, subscription, "workspace_inactive").

Success:

When everything is valid and active:

returns (workspace, api_key, subscription, None).

All of this behavior is asserted in tests/test_saas_auth.py.

4. HTTP auth integration (FastAPI dependency)
4.1 get_current_workspace dependency

Implementation: services/app_server/saas_http.py.

Signature:

async def get_current_workspace(
    request: Request,
    registry: InMemorySaasRegistry = Depends(get_saas_registry),
) -> Workspace:
    ...


Behavior:

Read headers:

Authorization

or X-API-Key (fallback if Authorization missing).

Call resolve_workspace_from_header(registry, header_value).

Map errors to HTTP responses:

missing_token or invalid_token → HTTPException(status_code=401)

workspace_inactive → HTTPException(status_code=403)

Success → returns a Workspace instance.

Tests:

tests/test_saas_http_auth.py::test_saas_http_auth_with_authorization_header

tests/test_saas_http_auth.py::test_saas_http_auth_missing_token

tests/test_saas_http_auth.py::test_saas_http_auth_inactive_workspace

validate:

Authorization: Bearer velu_123 → 200 OK when workspace active.

No headers → 401.

Header pointing to inactive workspace → 403.

4.2 Example usage in an app

A typical endpoint might look like:

from fastapi import APIRouter, Depends
from services.app_server.saas_http import get_current_workspace
from services.app_server.schemas.saas import Workspace  # type: ignore

router = APIRouter()

@router.get("/whoami")
def whoami(workspace: Workspace = Depends(get_current_workspace)):
    return {
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "plan": workspace.plan,
        "is_active": workspace.is_active,
    }


As long as the registry is seeded with a workspace and an active API key, this endpoint will resolve the workspace from incoming requests.

5. Sandbox example: minimal SaaS demo

You can run a small stand-alone app to see SaaS auth working outside the test suite.

Example file (see sandbox_saas_app.py in the repo root):

from fastapi import FastAPI, Depends
import uvicorn

from services.app_server.saas_http import (
    get_current_workspace,
    get_saas_registry,
)
from services.app_server.schemas.saas import Workspace, User, ApiKey  # type: ignore

app = FastAPI(title="Velu SaaS demo")

reg = get_saas_registry()

owner = User(
    id="user_1",
    email="owner@example.com",
    name="Owner User",
    is_active=True,
)
reg.add_user(owner)

ws = Workspace(
    id="ws_1",
    slug="demo-workspace",
    name="Demo Workspace",
    owner_user_id=owner.id,
    plan="pro",
    is_active=True,
)
reg.add_workspace(ws)

api_key = ApiKey(
    id="key_1",
    workspace_id=ws.id,
    key_prefix="velu_123",
    is_active=True,
)
reg.add_api_key(api_key)


@app.get("/whoami")
def whoami(workspace: Workspace = Depends(get_current_workspace)):
    return {
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "workspace_name": workspace.name,
        "plan": workspace.plan,
        "is_active": workspace.is_active,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8099)


Run:

python sandbox_saas_app.py


Then test:

curl -i -H "Authorization: Bearer velu_123" http://127.0.0.1:8099/whoami

6. Where this fits in Phase 12

This SaaS auth layer is the foundation for:

Multi-tenant Velu console

Per-workspace API keys

Subscription / plan enforcement

Future billing integration (Stripe, etc.)

All core logic is now covered by tests and documented here, so higher-level features can safely build on top of it.