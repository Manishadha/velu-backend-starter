from __future__ import annotations

from typing import Any

from services.queue import queue_api


def using_postgres() -> bool:
    from services.queue import using_postgres_jobs

    return using_postgres_jobs()


def ensure_schema() -> None:
    queue_api.ensure_schema()


def enqueue(
    *,
    task: str,
    payload: dict[str, Any] | None = None,
    priority: int = 0,
    key: str | None = None,
    org_id: str | None = None,
    project_id: str | None = None,
    created_by: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> str | int:
    return queue_api.enqueue(
        task=task,
        payload=payload,
        priority=priority,
        key=key,
        org_id=org_id,
        project_id=project_id,
        created_by=created_by,
        actor_type=actor_type,
        actor_id=actor_id,
    )


def enqueue_job(
    task_obj: dict[str, Any],
    *,
    org_id: str | None = None,
    project_id: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    priority: int = 0,
    key: str | None = None,
    created_by: str | None = None,
) -> str | int:
    t = ""
    payload: dict[str, Any] = {}
    if isinstance(task_obj, dict):
        t = str(task_obj.get("task") or "")
        pl = task_obj.get("payload")
        if isinstance(pl, dict):
            payload = pl
        if actor_type is None and task_obj.get("actor_type"):
            actor_type = str(task_obj.get("actor_type"))
        if actor_id is None and task_obj.get("actor_id"):
            actor_id = str(task_obj.get("actor_id"))
    if actor_id is not None:
        created_by = str(actor_id)
    return queue_api.enqueue(
        task=t,
        payload=payload,
        priority=int(priority),
        key=key,
        org_id=org_id,
        project_id=project_id,
        created_by=created_by,
        actor_type=actor_type,
        actor_id=actor_id,
    )

def claim_one_job(*, worker_id: str = "worker", lease_seconds: int = 300) -> dict[str, Any] | None:
    return queue_api.claim_one_job(worker_id=worker_id, lease_seconds=lease_seconds)


def heartbeat(*, job_id: str, worker_id: str | None = None, lease_seconds: int = 300) -> bool:
    return bool(queue_api.heartbeat(job_id=str(job_id), worker_id=worker_id, lease_seconds=int(lease_seconds)))


def requeue_expired(limit: int = 25) -> int:
    return int(queue_api.requeue_expired(limit=int(limit)))


def finish_job(job_id: str | int, result: dict[str, Any]) -> None:
    queue_api.finish_job(job_id, result)


def fail_job(job_id: str | int, error: Any) -> None:
    queue_api.fail_job(job_id, error)


def load(job_id: Any) -> dict[str, Any] | None:
    return queue_api.get(job_id)


def get_job(job_id: Any) -> dict[str, Any] | None:
    return queue_api.get(job_id)


def project_belongs_to_org(project_id: str, org_id: str) -> bool:
    from services.queue import jobs_postgres, jobs_sqlite, using_postgres_jobs

    if using_postgres_jobs():
        return bool(jobs_postgres.project_belongs_to_org(project_id, org_id))
    return bool(jobs_sqlite.project_belongs_to_org(project_id, org_id))


def list_recent_for_org(*, org_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return list(queue_api.list_recent_for_org(org_id=str(org_id), limit=int(limit)))


def list_recent(limit: int = 50) -> list[dict[str, Any]]:
    return list(queue_api.list_recent(limit=int(limit)))
