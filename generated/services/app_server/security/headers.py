from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request, call_next: Callable):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-site"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        )
        return resp
