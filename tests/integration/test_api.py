import json

from fastapi.testclient import TestClient

from services.app_server.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("app") == "velu"


def test_tasks_accept_and_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_LOG", str(tmp_path / "tasks.log"))
    payload = {"task": "plan", "payload": {"p": "q"}}
    r = client.post("/tasks", json=payload)
    assert r.status_code == 200
    out = r.json()
    assert out.get("ok") is True
    assert isinstance(out.get("job_id"), str)
    assert out.get("job_id")

    log = (tmp_path / "tasks.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(log) >= 1
    rec = json.loads(log[-1])
    assert rec["task"] == "plan"
    assert rec["payload"] == {"p": "q"}
