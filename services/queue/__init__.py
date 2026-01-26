from __future__ import annotations

import importlib
from typing import Any

import os

def using_postgres_jobs() -> bool:
    v = (os.getenv("VELU_JOBS_BACKEND") or "").strip().lower()
    if v:
        return v == "postgres"

    url = (os.getenv("DATABASE_URL") or "").strip().lower()
    if url.startswith("postgresql://") or url.startswith("postgresql+psycopg://") or url.startswith("postgres://"):
        return True

    return (os.getenv("DB_ENGINE") or "").strip().lower() == "postgres"


def get_queue() -> Any:
    """
    Central queue selector used across agents/app/worker.

    Always return the stable wrapper API (enqueue/load/get/list_recent/claim_one_job),
    which internally routes to sqlite or postgres via jobs_sqlite.
    """
    return importlib.import_module("services.queue.queue_api")


__all__ = ["get_queue", "using_postgres_jobs"]
