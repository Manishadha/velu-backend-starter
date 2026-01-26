from fastapi import FastAPI

from .routes import health, ai


def create_app() -> FastAPI:
    app = FastAPI(title="Velu API", version="0.1.0")

    try:
        from .security.headers import install_security_middleware  # type: ignore
    except ImportError:
        install_security_middleware = None

    if install_security_middleware is not None:
        install_security_middleware(app)

    app.include_router(health.router, prefix="")
    app.include_router(ai.router, prefix="")

    return app


app = create_app()
