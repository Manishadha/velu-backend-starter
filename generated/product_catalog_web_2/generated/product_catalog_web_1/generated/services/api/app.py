from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, products, cart, ai, auth, i18n


def create_app() -> FastAPI:
    app = FastAPI(title="Generated API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3006",
            "http://127.0.0.1:3006",
            "http://localhost:3010",
            "http://127.0.0.1:3010",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(products.router)
    app.include_router(cart.router)
    app.include_router(ai.router)
    app.include_router(auth.router)
    app.include_router(i18n.router)

    return app


app = create_app()
