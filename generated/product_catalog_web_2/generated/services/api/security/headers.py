from __future__ import annotations

from fastapi import FastAPI, Request, Response


_DEFAULT_CSP = "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"


def _set_if_missing(response: Response, name: str, value: str) -> None:
    if name not in response.headers:
        response.headers[name] = value


def install_security_middleware(app: FastAPI, *, csp: str | None = None) -> None:
    policy = csp or _DEFAULT_CSP

    @app.middleware("http")
    async def _security_middleware(request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        _set_if_missing(response, "X-Content-Type-Options", "nosniff")
        _set_if_missing(response, "Referrer-Policy", "strict-origin-when-cross-origin")
        _set_if_missing(response, "X-Frame-Options", "DENY")
        _set_if_missing(response, "Cross-Origin-Opener-Policy", "same-origin")
        _set_if_missing(response, "Cross-Origin-Resource-Policy", "same-origin")
        _set_if_missing(response, "Permissions-Policy", "geolocation=(), microphone=()")
        _set_if_missing(response, "Content-Security-Policy", policy)
        return response
