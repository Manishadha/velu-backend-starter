# services/queue/jobs_postgres.py
from __future__ import annotations

import os
from contextlib import closing
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _db_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is required for Postgres jobs backend")

    low = raw.lower()
    if low.startswith("postgresql+psycopg://"):
        return "postgresql://" + raw.split("://", 1)[1]
    if low.startswith("postgres://"):
        return "postgresql://" + raw.split("://", 1)[1]
    return raw


def _connect() -> psycopg.Connection:
    return psycopg.connect(_db_url(), row_factory=dict_row)


def ensure_schema() -> None:
    # migrations handle schema
    return


def enqueue(*, task, payload=None, priority=0, key=None):
    raise RuntimeError(
        "services.queue.jobs_postgres.enqueue() is not supported in Postgres jobs mode. "
        "Use services.queue.jobs.enqueue_job(task_obj, org_id=..., project_id=...) instead."
    )


def enqueue_job(
    task_obj: dict[str, Any],
    *,
    org_id: str,
    project_id: str | None = None,
    actor_type: str = "api_key",
    actor_id: str | None = None,
    priority: int = 0,
) -> str:
    task = (task_obj.get("task") or "").strip()
    payload = task_obj.get("payload") or {}

    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs_v2 (
                  org_id, project_id, task, status, payload, priority, actor_type, actor_id
                )
                VALUES (
                  %s::uuid, %s::uuid, %s, 'queued', %s::jsonb, %s, %s, %s
                )
                RETURNING id::text AS id;
                """,
                (
                    str(org_id),
                    str(project_id) if project_id else None,
                    task,
                    Jsonb(payload),
                    int(priority),
                    str(actor_type or "api_key"),
                    str(actor_id) if actor_id else None,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return str(row["id"])


def get_job(job_id: str) -> dict[str, Any] | None:
    if not job_id:
        return None
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT *, id::text AS id FROM jobs_v2 WHERE id=%s::uuid LIMIT 1;",
                (str(job_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_job_for_org(job_id: str, org_id: str) -> dict[str, Any] | None:
    if not job_id or not org_id:
        return None
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *, id::text AS id
                FROM jobs_v2
                WHERE id=%s::uuid AND org_id=%s::uuid
                LIMIT 1;
                """,
                (str(job_id), str(org_id)),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def project_belongs_to_org(project_id: str, org_id: str) -> bool:
    if not project_id or not org_id:
        return False
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM projects WHERE id=%s::uuid AND org_id=%s::uuid LIMIT 1;",
                (str(project_id), str(org_id)),
            )
            return cur.fetchone() is not None


def list_recent_for_org(*, org_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *, id::text AS id
                FROM jobs_v2
                WHERE org_id=%s::uuid
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (str(org_id), int(limit)),
            )
            return [dict(r) for r in (cur.fetchall() or [])]


def claim_one_job(*, worker_id: str = "worker", lease_seconds: int = 300) -> dict[str, Any] | None:
    """
    Phase 1: atomic claim + reclaim expired leases.
    - picks queued jobs OR working jobs whose lease expired
    - marks as working and sets lease_expires_at
    """
    wid = (worker_id or "").strip() or "worker"
    lease_s = max(5, int(lease_seconds or 300))

    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH picked AS (
                  SELECT id
                  FROM jobs_v2
                  WHERE
                    status = 'queued'
                    OR (
                      status = 'working'
                      AND lease_expires_at IS NOT NULL
                      AND lease_expires_at < now()
                    )
                  ORDER BY priority DESC, created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE jobs_v2 j
                SET status='working',
                    attempts=COALESCE(attempts, 0) + 1,
                    claimed_by=%s,
                    claimed_at=now(),
                    lease_expires_at=now() + (%s::int * interval '1 second'),
                    updated_at=now()
                FROM picked
                WHERE j.id = picked.id
                RETURNING j.*, j.id::text AS id;
                """,
                (wid, lease_s),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None


def finish_job(job_id: str, result: dict[str, Any]) -> None:
    if not job_id:
        return
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jobs_v2
                SET status='done',
                    result=%s::jsonb,
                    error=NULL,
                    finished_at=now(),
                    lease_expires_at=NULL,
                    updated_at=now()
                WHERE id=%s::uuid;
                """,
                (Jsonb(result or {}), str(job_id)),
            )
            conn.commit()


def fail_job(job_id: str, error: Any) -> None:
    if not job_id:
        return
    payload = error if isinstance(error, (dict, list)) else {"message": str(error)}
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jobs_v2
                SET status='error',
                    error=%s::jsonb,
                    finished_at=now(),
                    lease_expires_at=NULL,
                    updated_at=now()
                WHERE id=%s::uuid;
                """,
                (Jsonb(payload), str(job_id)),
            )
            conn.commit()



load = get_job
get = get_job
