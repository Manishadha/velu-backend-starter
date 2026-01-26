from __future__ import annotations

from services.app_server.schemas.blueprint import (  # type: ignore
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)


def test_blueprint_minimal() -> None:
    bp = Blueprint(
        id="demo_app",
        name="Demo App",
        kind="web_app",
        frontend=BlueprintFrontend(
            framework="nextjs",
            language="typescript",
            targets=["web", "android"],
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
            supported_languages=["en", "fr", "nl", "de", "ar", "ta"],
        ),
    )

    assert bp.id == "demo_app"
    assert bp.frontend.targets == ["web", "android"]
    assert bp.localization.default_language == "en"
    assert "fr" in bp.localization.supported_languages
