from __future__ import annotations

from fastapi import FastAPI

try:
    from services.api.app import create_app as _base_create_app
except ImportError:
    _base_create_app = None


def create_app() -> FastAPI:
    if _base_create_app is not None:
        app = _base_create_app()
    else:
        app = FastAPI(title="Velu Generated App", version="0.1.0")

        @app.get("/health")
        async def health() -> dict[str, object]:
            return {"ok": True, "app": "generated"}

    @app.get("/ready")
    async def ready() -> dict[str, object]:
        return {"ok": True}

    return app


app = create_app()
