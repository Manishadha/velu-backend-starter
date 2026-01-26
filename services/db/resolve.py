from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache
def database_url() -> str:
    explicit = (os.getenv("DATABASE_URL") or "").strip()
    if explicit:
        return explicit

    task_db = (os.getenv("TASK_DB") or "").strip()
    if task_db:
        if "://" in task_db:
            return task_db
        path = Path(task_db)
        return f"sqlite:///{path.absolute()}"

    default = Path.cwd() / "data" / "jobs.db"
    default.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{default.absolute()}"


def sqlite_path() -> str:
    url = database_url()
    if not url.startswith("sqlite:///"):
        raise RuntimeError("sqlite_path() called but DATABASE_URL is not sqlite")
    return url.removeprefix("sqlite:///")
