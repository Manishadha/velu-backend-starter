# services/api/db.py
from __future__ import annotations

import os
from pathlib import Path


def database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        return raw

    engine = (os.getenv("DB_ENGINE") or "").strip().lower()
    if engine in {"postgres", "postgresql"}:
        user = (os.getenv("APP_POSTGRES_USER") or "app_user").strip()
        pw = (os.getenv("APP_POSTGRES_PASSWORD") or "app_pass").strip()
        host = (os.getenv("APP_POSTGRES_HOST") or "localhost").strip()
        port = (os.getenv("APP_POSTGRES_PORT") or "5432").strip()
        db = (os.getenv("APP_POSTGRES_DB") or "app_db").strip()
        return f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"

    Path("data").mkdir(parents=True, exist_ok=True)
    return "sqlite:///./data/app.db"


def _cache_clear() -> None:
    return None


database_url.cache_clear = _cache_clear  # type: ignore[attr-defined]
