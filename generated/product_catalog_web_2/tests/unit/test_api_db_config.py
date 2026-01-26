from __future__ import annotations

import os  # noqa: F401
from pathlib import Path

from services.api import db


def test_database_url_default_sqlite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_ENGINE", "sqlite")
    monkeypatch.chdir(tmp_path)

    url = db.database_url()
    assert url == "sqlite:///./data/app.db"
    assert (tmp_path / "data").is_dir()


def test_database_url_postgres(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_ENGINE", "postgres")

    db.database_url.cache_clear()  # type: ignore[attr-defined]
    url = db.database_url()
    assert url == "postgresql+psycopg://app_user:app_pass@localhost:5432/app_db"


def test_database_url_explicit(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/custom")
    monkeypatch.setenv("DB_ENGINE", "sqlite")

    db.database_url.cache_clear()  # type: ignore[attr-defined]
    url = db.database_url()
    assert url == "postgresql://user:pass@db:5432/custom"
