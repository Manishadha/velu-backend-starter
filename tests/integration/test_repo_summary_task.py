# tests/integration/test_repo_summary_task.py
import sqlite3
from contextlib import closing

from starlette.testclient import TestClient

from services.app_server.main import create_app
from services.queue import jobs_sqlite
from services.queue import worker_entry


def _client() -> TestClient:
    app = create_app()
    return TestClient(app)


def _run_one_job() -> bool:
    """
    Run exactly one queued job using the same internal worker logic,
    without starting the infinite worker loop.
    """
    # Make sure schema exists for this isolated TASK_DB
    jobs_sqlite.ensure_schema()

    db_path = jobs_sqlite.db_path()
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row

        row = worker_entry._claim_one_job(conn)  # intentional: internal helper
        if not row:
            return False

        job_id = int(row["id"])
        try:
            result = worker_entry._process_task(row)  # intentional internal helper
            worker_entry._complete_job(conn, job_id, result, None)  # intentional
        except Exception as exc:
            worker_entry._complete_job(conn, job_id, None, {"error": str(exc)})  # intentional

        return True


def test_repo_summary_task(tmp_path, monkeypatch):
    # Isolated DB/log for this test run
    monkeypatch.setenv("TASK_DB", str(tmp_path / "jobs.db"))
    monkeypatch.setenv("TASK_LOG", str(tmp_path / "tasks.log"))

    c = _client()

    r = c.post(
        "/tasks",
        json={
            "task": "repo_summary",
            "payload": {
                "root": ".",
                "focus_dirs": ["services", "tests"],
                "include_snippets": False,
            },
        },
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    # No real worker thread/process is running in this test,
    # so manually execute one queued job.
    assert _run_one_job() is True

    rr = c.get(f"/results/{job_id}?expand=1")
    assert rr.status_code == 200, rr.text
    item = rr.json().get("item") or rr.json()

    assert item["status"] == "done", item
    assert item["task"] == "repo_summary"
    assert item["result"]["ok"] is True
    assert item["result"]["stats"]["total_files_seen"] >= 1
