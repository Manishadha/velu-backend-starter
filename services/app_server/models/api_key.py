# services/app_server/models/api_key.py
from __future__ import annotations

import base64
import hashlib
import os


def _pepper() -> bytes:
    """
    Optional extra secret used in hashing.
    If unset, hashing still works, just without pepper.
    """
    return (os.getenv("VELU_API_KEY_PEPPER") or "").encode("utf-8")


def hash_key(raw: str) -> str:
    """
    Stable DB-safe hash for API key lookup.

    IMPORTANT:
    - Must match everywhere (create + lookup).
    - Uses SHA-256 over (pepper + raw).
    - Stored as base64url without '=' padding.
    """
    raw = (raw or "").strip()
    digest = hashlib.sha256(_pepper() + raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def mask_key(raw: str) -> str:
    """
    Safe key display: never return full key.
    Example: velu_abcd...wxyz
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    if len(raw) <= 12:
        return raw[:2] + "..." + raw[-2:]
    return raw[:8] + "..." + raw[-4:]
