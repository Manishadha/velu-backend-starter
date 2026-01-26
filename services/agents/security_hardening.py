from __future__ import annotations

from typing import Any, Dict, List

_CSP = "default-src 'self'; " "frame-ancestors 'none'; " "object-src 'none'; " "base-uri 'self'"

_APP_SERVER_MW = f"""from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next: Callable):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-site"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        resp.headers["Content-Security-Policy"] = "{_CSP}"
        return resp
"""

_GENERATED_API_MW = f"""from __future__ import annotations

from fastapi import FastAPI, Request, Response


_DEFAULT_CSP = "{_CSP}"


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
"""


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    files: List[Dict[str, str]] = [
        {
            "path": "services/app_server/security/headers.py",
            "content": _APP_SERVER_MW,
        },
        {
            "path": "generated/services/api/security/headers.py",
            "content": _GENERATED_API_MW,
        },
    ]
    return {"ok": True, "agent": "security_hardening", "files": files}
