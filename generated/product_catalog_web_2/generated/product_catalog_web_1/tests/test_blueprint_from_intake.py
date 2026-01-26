from __future__ import annotations

from services.app_server.schemas.blueprint import Blueprint  # type: ignore
from services.app_server.schemas.blueprint_factory import blueprint_from_intake  # type: ignore
from services.app_server.schemas.intake import Company, Intake, Product


def test_blueprint_from_intake_basic() -> None:
    company = Company(name="Velu AI", industry="software")
    product = Product(
        type="saas",
        goal="internal_tool",
        audiences=["devs"],
        channels=["web", "android"],
        locales=["en", "fr", "nl"],
    )
    intake = Intake(company=company, product=product)

    bp = blueprint_from_intake(intake)

    assert isinstance(bp, Blueprint)
    assert bp.id == "velu_ai"
    assert bp.kind == "web_app"
    assert "web" in bp.frontend.targets
    assert "android" in bp.frontend.targets
    assert bp.localization.default_language == "en"
    assert bp.localization.supported_languages == ["en", "fr", "nl"]
    assert bp.backend.framework == "fastapi"
    assert bp.database.engine == "sqlite"
