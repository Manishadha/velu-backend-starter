from __future__ import annotations

from fastapi.testclient import TestClient

from services.app_server.main import create_app
from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)


client = TestClient(create_app())


def _sample_blueprint() -> Blueprint:
    return Blueprint(
        id="bp_demo",
        name="Demo Blueprint",
        kind="web_app",
        frontend=BlueprintFrontend(
            framework="nextjs",
            language="typescript",
            targets=["web"],
        ),
        backend=BlueprintBackend(
            framework="fastapi",
            language="python",
            style="rest",
        ),
        database=BlueprintDatabase(
            engine="sqlite",
            mode="single_node",
        ),
        localization=BlueprintLocalization(
            default_language="en",
            supported_languages=["en", "fr"],
        ),
    )


def test_blueprint_save_and_get() -> None:
    bp = _sample_blueprint()

    resp = client.post("/v1/blueprints/save", json=bp.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["id"] == "bp_demo"

    resp2 = client.get("/v1/blueprints/bp_demo")
    assert resp2.status_code == 200
    got = resp2.json()
    assert got["id"] == "bp_demo"
    assert got["name"] == "Demo Blueprint"
    assert got["frontend"]["framework"] == "nextjs"
    assert got["backend"]["framework"] == "fastapi"


def test_blueprint_list_contains_saved() -> None:
    resp = client.get("/v1/blueprints?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("items") or []
    ids = {it.get("id") or it.get("body", {}).get("id") for it in items}
    assert "bp_demo" in ids
