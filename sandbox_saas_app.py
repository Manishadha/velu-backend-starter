from fastapi import FastAPI, Depends
import uvicorn

from services.app_server.saas_http import (
    get_current_workspace,
    get_saas_registry,
)
from services.app_server.schemas.saas import (  # type: ignore
    Workspace,
    User,
    ApiKey,
)

app = FastAPI(title="Velu SaaS demo")

# Use the global in-memory registry
reg = get_saas_registry()

# 1) Demo owner user
owner = User(
    id="user_1",
    email="owner@example.com",
    name="Owner User",
    is_active=True,
)
reg.add_user(owner)

# 2) Demo workspace
ws = Workspace(
    id="ws_1",
    slug="demo-workspace",
    name="Demo Workspace",
    owner_user_id=owner.id,
    plan="pro",
    is_active=True,
)
reg.add_workspace(ws)

# 3) Demo API key with prefix "velu_123"
#    NOTE: name + hashed_secret are required by the model.
api_key = ApiKey(
    id="key_1",
    workspace_id=ws.id,
    key_prefix="velu_123",
    name="Default key",
    hashed_secret="dummy-hash",  # not used in tests / demo
    is_active=True,
)
reg.add_api_key(api_key)


@app.get("/whoami")
def whoami(workspace: Workspace = Depends(get_current_workspace)):
    """
    Simple endpoint that returns the current workspace,
    resolved from Authorization / X-API-Key headers.
    """
    return {
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "workspace_name": workspace.name,
        "plan": workspace.plan,
        "is_active": workspace.is_active,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8099)
