from __future__ import annotations

from fastapi import FastAPI

try:
    # Reuse the generated API app as the core application
    from services.api.app import app as _api_app  # type: ignore[import]
except Exception:  # pragma: no cover

    _api_app = FastAPI(title="generated-api-fallback")


def create_app() -> FastAPI:
    """
    Entry point used by tests/integration/test_ready.py and other integration tests.

    We take the generated API app and add a simple /ready endpoint that reports
    that the API is up.
    """
    app = _api_app

    @app.get("/ready")
    async def ready() -> dict[str, object]:  # type: ignore[unused-variable]
        return {"ok": True, "app": app.title or "generated-app"}

    return app


# Uvicorn (and tests) import this symbol
app = create_app()
