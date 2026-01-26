from __future__ import annotations

from fastapi.testclient import TestClient

from services.app_server.main import app

client = TestClient(app)


def test_blueprint_design_basic() -> None:
    payload = {
        "id": "demo_app",
        "name": "Demo App",
        "kind": "web_app",
        "frontend": {
            "framework": "nextjs",
            "language": "typescript",
            "targets": ["web"],
        },
        "backend": {
            "framework": "fastapi",
            "language": "python",
            "style": "rest",
        },
        "database": {
            "engine": "sqlite",
            "mode": "single_node",
        },
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "fr"],
        },
    }

    resp = client.post("/v1/blueprints/design", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "blueprint" in data
    assert "architecture" in data

    bp = data["blueprint"]
    arch = data["architecture"]

    # Blueprint echoes normalized input
    assert bp["id"] == "demo_app"
    assert bp["name"] == "Demo App"
    assert bp["kind"] == "web_app"
    assert bp["frontend"]["framework"] == "nextjs"
    assert bp["backend"]["framework"] == "fastapi"
    assert bp["database"]["engine"] == "sqlite"

    # Architecture mirrors core fields + has a human summary
    assert arch["id"] == "demo_app"
    assert arch["name"] == "Demo App"
    assert arch["kind"] == "web_app"
    assert "Frontend:" in arch["summary"]
    assert "Backend:" in arch["summary"]
    assert "Database:" in arch["summary"]
