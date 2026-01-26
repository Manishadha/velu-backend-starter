from __future__ import annotations

from services.app_server.schemas.blueprint_factory import (
    blueprint_from_hospital_spec,
)


def test_doc_example_web_dashboard_spec() -> None:
    """
    Doc example #1:
    Web dashboard with Next.js + FastAPI + SQLite.
    """
    spec = {
        "project": {
            "id": "team_dashboard",
            "name": "Team Dashboard",
            "type": "dashboard",
        },
        "stack": {
            "frontend": {
                "framework": "nextjs",
                "language": "typescript",
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
    }

    bp = blueprint_from_hospital_spec(spec)

    # Basic identity
    assert bp.id == "team_dashboard"
    assert bp.name == "Team Dashboard"

    # Kind normalization
    assert bp.kind == "dashboard"

    # Frontend
    assert bp.frontend.framework == "nextjs"
    assert bp.frontend.language == "typescript"
    assert bp.frontend.targets == ["web"]

    # Backend
    assert bp.backend.framework == "fastapi"
    assert bp.backend.language == "python"
    assert bp.backend.style == "rest"

    # Database
    assert bp.database.engine == "sqlite"
    assert bp.database.mode == "single_node"

    # Localization
    assert bp.localization.default_language == "en"
    assert bp.localization.supported_languages == ["en", "fr"]


def test_doc_example_mobile_multiplatform_spec() -> None:
    """
    Doc example #2:
    Mobile shopping app with React Native + Express + Postgres.
    """
    spec = {
        "project": {
            "id": "shopping_app",
            "name": "Shopping App",
            "type": "mobile_app",
        },
        "stack": {
            "frontend": {
                "framework": "react_native",
                "language": "typescript",
            },
            "backend": {
                "framework": "express",
                "language": "typescript",
                "style": "rest",
            },
            "database": {
                "engine": "postgres",
                "mode": "clustered",
            },
        },
        "localization": {
            "default_language": "nl",
            "supported_languages": ["nl", "en", "fr"],
        },
    }

    bp = blueprint_from_hospital_spec(spec)

    # Basic identity
    assert bp.id == "shopping_app"
    assert bp.name == "Shopping App"

    # Kind + targets for mobile
    assert bp.kind == "mobile_app"
    # React Native or "mobile_app" kind => android + ios
    assert bp.frontend.framework == "react_native"
    assert bp.frontend.language == "typescript"
    assert bp.frontend.targets == ["android", "ios"]

    # Backend
    assert bp.backend.framework == "express"
    # For express we expect the language we passed in
    assert bp.backend.language == "typescript"
    assert bp.backend.style == "rest"

    # Database
    assert bp.database.engine == "postgres"
    assert bp.database.mode == "clustered"

    # Localization
    assert bp.localization.default_language == "nl"
    assert bp.localization.supported_languages == ["nl", "en", "fr"]
