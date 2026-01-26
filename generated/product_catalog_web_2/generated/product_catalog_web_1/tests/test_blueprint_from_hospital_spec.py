from __future__ import annotations

from services.app_server.schemas.blueprint import Blueprint  # type: ignore
from services.app_server.schemas.blueprint_factory import blueprint_from_hospital_spec  # type: ignore


def test_blueprint_from_hospital_spec_web_app() -> None:
    spec = {
        "project": {
            "id": "hospital_mgmt_v1",
            "name": "Hospital Management Web App",
            "type": "web_app",
            "description": "Demo spec",
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
                "engine": "postgres",
                "mode": "single_node",
            },
        },
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "fr", "de"],
        },
        "features": {
            "modules": ["patients", "appointments"],
        },
    }

    bp = blueprint_from_hospital_spec(spec)

    assert isinstance(bp, Blueprint)
    assert bp.id == "hospital_mgmt_v1"
    assert bp.name == "Hospital Management Web App"
    assert bp.kind == "web_app"
    assert bp.frontend.framework == "nextjs"
    assert "web" in bp.frontend.targets
    assert "android" not in bp.frontend.targets
    assert bp.backend.framework == "fastapi"
    assert bp.database.engine == "postgres"
    assert bp.localization.default_language == "en"
    assert bp.localization.supported_languages == ["en", "fr", "de"]


def test_blueprint_from_hospital_spec_mobile_targets() -> None:
    spec = {
        "project": {
            "id": "hospital_mobile_v1",
            "name": "Hospital Mobile",
            "type": "mobile_app",
        },
        "stack": {
            "frontend": {"framework": "react"},
            "backend": {"framework": "express"},
            "database": {"engine": "sqlite"},
        },
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "ar"],
        },
    }

    bp = blueprint_from_hospital_spec(spec)

    assert bp.kind == "mobile_app"
    assert "android" in bp.frontend.targets
    assert "ios" in bp.frontend.targets
    assert bp.backend.language in {"node", "javascript"}
