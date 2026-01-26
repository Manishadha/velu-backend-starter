from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from services.queue import jobs_postgres, jobs_sqlite, using_postgres_jobs


def ensure_schema() -> None:
    if using_postgres_jobs():
        jobs_postgres.ensure_schema()
    else:
        jobs_sqlite.ensure_schema()


def enqueue(
    task_obj: Dict[str, Any] | None = None,
    *,
    task: str | None = None,
    payload: Dict[str, Any] | None = None,
    priority: int = 0,
    key: str | None = None,
    org_id: str | None = None,
    project_id: str | None = None,
    created_by: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    require_tenant: bool = False,
) -> str | int:
    if task is None:
        if isinstance(task_obj, dict):
            task = str(task_obj.get("task") or "")
            pl = task_obj.get("payload")
            if isinstance(pl, dict):
                payload = pl
        if task is None:
            task = ""
    if payload is None:
        payload = {}

    if using_postgres_jobs():
        if require_tenant and not org_id:
            raise RuntimeError("enqueue() requires org_id when using Postgres jobs backend")
        if not org_id:
            raise RuntimeError("enqueue() requires org_id when using Postgres jobs backend")
        at = str(actor_type or "api_key")
        aid = str(actor_id) if actor_id else (str(created_by) if created_by else None)
        return jobs_postgres.enqueue_job(
            {"task": task, "payload": payload},
            org_id=str(org_id),
            project_id=str(project_id) if project_id else None,
            actor_type=at,
            actor_id=aid,
            priority=int(priority),
        )

    return jobs_sqlite.enqueue_job(
        {"task": task, "payload": payload},
        key=key,
        priority=int(priority),
        org_id=org_id,
        project_id=project_id,
        created_by=created_by,
        actor_type=actor_type,
        actor_id=actor_id,
        require_tenant=require_tenant,
    )


enqueue_job = enqueue


def load(job_id: Any) -> Dict[str, Any]:
    rec = get(job_id)
    return rec or {}


def get(job_id: Any) -> Optional[Dict[str, Any]]:
    if using_postgres_jobs():
        return jobs_postgres.get_job(str(job_id))
    return jobs_sqlite.get_job(job_id)


def get_job(job_id: Any) -> Optional[Dict[str, Any]]:
    return get(job_id)


def get_job_for_org(job_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    if using_postgres_jobs():
        fn = getattr(jobs_postgres, "get_job_for_org", None)
        if fn is None:
            return jobs_postgres.get_job(str(job_id))
        return fn(str(job_id), str(org_id))
    fn2 = getattr(jobs_sqlite, "get_job_for_org", None)
    if fn2 is None:
        return jobs_sqlite.get_job(job_id)
    return fn2(str(job_id), str(org_id))


def list_recent(limit: int = 50) -> Iterable[Dict[str, Any]]:
    if using_postgres_jobs():
        return []
    return jobs_sqlite.list_recent(limit=limit)


def list_recent_for_org(*, org_id: str, limit: int = 50) -> Iterable[Dict[str, Any]]:
    if using_postgres_jobs():
        fn = getattr(jobs_postgres, "jobs_list_recent_for_org", None) or getattr(
            jobs_postgres, "list_recent_for_org", None
        )
        if fn is None:
            return []
        return fn(org_id=str(org_id), limit=int(limit))
    return jobs_sqlite.list_recent_for_org(org_id=org_id, limit=limit)

def claim_one_job(*, worker_id: str = "worker", lease_seconds: int = 300) -> Dict[str, Any] | None:
    if using_postgres_jobs():
        return jobs_postgres.claim_one_job(worker_id=worker_id, lease_seconds=lease_seconds)
    ensure_schema()
    return jobs_sqlite.claim_one_job()



def heartbeat(*, job_id: str, worker_id: str | None = None, lease_seconds: int = 300) -> bool:
    if not using_postgres_jobs():
        return True
    fn = getattr(jobs_postgres, "heartbeat", None)
    if fn is None:
        return True
    try:
        return bool(fn(job_id=str(job_id), worker_id=worker_id, lease_seconds=int(lease_seconds)))
    except TypeError:
        try:
            return bool(fn(job_id=str(job_id)))
        except TypeError:
            return True


def requeue_expired(limit: int = 25) -> int:
    if not using_postgres_jobs():
        return 0
    fn = getattr(jobs_postgres, "requeue_expired", None)
    if fn is None:
        return 0
    try:
        return int(fn(limit=int(limit)))
    except TypeError:
        return int(fn())


def finish_job(job_id: str | int, result: Dict[str, Any]) -> None:
    if using_postgres_jobs():
        fn = getattr(jobs_postgres, "finish_job", None)
        if fn is None:
            raise RuntimeError("Postgres jobs backend missing finish_job()")
        fn(str(job_id), result)
        return
    jobs_sqlite.finish_job(job_id, result)


def fail_job(job_id: str | int, error: Any) -> None:
    if using_postgres_jobs():
        fn = getattr(jobs_postgres, "fail_job", None)
        if fn is None:
            raise RuntimeError("Postgres jobs backend missing fail_job()")
        fn(str(job_id), error)
        return
    jobs_sqlite.fail_job(job_id, error)
