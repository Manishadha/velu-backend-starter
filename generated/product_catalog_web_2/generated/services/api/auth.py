from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

SECRET_KEY = os.getenv("VELU_AUTH_SECRET", "change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(claims: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = dict(claims)
    if "exp" not in payload:
        payload["exp"] = int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    payload.setdefault("iat", int(now.timestamp()))

    header = {"alg": ALGORITHM, "typ": "JWT"}

    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _b64url_encode(header_bytes)
    payload_b64 = _b64url_encode(payload_bytes)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


class AuthError(Exception):
    pass


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise AuthError("invalid token structure") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        received_sig = _b64url_decode(signature_b64)
    except Exception as exc:  # pragma: no cover
        raise AuthError("invalid signature encoding") from exc

    if not hmac.compare_digest(expected_sig, received_sig):
        raise AuthError("invalid signature")

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload: Dict[str, Any] = json.loads(payload_bytes)
    except Exception as exc:  # pragma: no cover
        raise AuthError("invalid payload") from exc

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts > float(exp):
            raise AuthError("token expired")

    return payload


class CurrentUser(BaseModel):
    id: str
    email: str
    roles: list[str] = []


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> CurrentUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )

    token = parts[1]
    try:
        payload = decode_access_token(token)
    except AuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    sub = str(payload.get("sub") or payload.get("id") or "")
    email = str(payload.get("email") or "")
    roles_raw = payload.get("roles") or []

    if isinstance(roles_raw, (list, tuple)):
        roles = [str(r) for r in roles_raw]
    elif roles_raw:
        roles = [str(roles_raw)]
    else:
        roles = []

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing subject in token",
        )

    return CurrentUser(id=sub, email=email, roles=roles)
