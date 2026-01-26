from __future__ import annotations

from fastapi.testclient import TestClient

from services.app_server.main import create_app
from services.app_server.schemas.intake import Company, Intake, Product

app = create_app()
client = TestClient(app)


def test_blueprint_from_intake_endpoint_basic() -> None:
    intake = Intake(
        company=Company(name="Demo Co"),
        product=Product(
            type="website",
            goal="lead_gen",
            audiences=["customers"],
            channels=["web"],
            locales=["en"],
        ),
    )

    resp = client.post("/v1/blueprints/from-intake", json=intake.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "company" in data
    assert "product" in data


def test_blueprint_from_hospital_endpoint_basic() -> None:
    spec = {
        "project": {
            "id": "hospital_mgmt_v1",
            "name": "Hospital Management Web App",
            "type": "web_app",
            "description": "demo hospital app",
        },
        "stack": {
            "frontend": {
                "framework": "nextjs",
                "language": "typescript",
                "ui_library": "tailwind_shadcn",
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
        },
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "fr"],
        },
        "features": {
            "modules": ["patients"],
            "auth": {
                "enabled": True,
                "roles": ["patient", "admin"],
                "login_methods": ["email_password"],
            },
        },
    }

    resp = client.post("/v1/blueprints/from-hospital", json=spec)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "product" in data
    assert "stack" in data
