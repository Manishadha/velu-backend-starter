from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="{{ title }}", version="{{ version }}")

    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        from .security.headers import install_security_middleware  # type: ignore[import]
    except ImportError:
        install_security_middleware = None

    if install_security_middleware is not None:
        install_security_middleware(app)

    from .routes import health, products, cart, ai, auth, i18n, assistant, rich

    app.include_router(health.router, prefix="")
    app.include_router(products.router, prefix="")
    app.include_router(cart.router, prefix="")
    app.include_router(ai.router, prefix="")
    app.include_router(auth.router, prefix="")
    app.include_router(i18n.router, prefix="")
    app.include_router(assistant.router, prefix="")
    app.include_router(rich.router, prefix="")

    return app


app = create_app()
