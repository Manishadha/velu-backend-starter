import json
from fastapi.testclient import TestClient
from services.app_server.main import create_app

def test_client_payload_not_polluted_in_recent_and_log(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_LOG", str(tmp_path / "tasks.log"))
    app = create_app()
    c = TestClient(app)

    r = c.post("/tasks", json={"task": "plan", "payload": {"x": 1}})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    # recent should show client payload only
    r2 = c.get("/tasks?limit=5")
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert items[0]["payload"] == {"x": 1}

    # TASK_LOG should show client payload only
    lines = (tmp_path / "tasks.log").read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(lines[-1])
    assert rec["payload"] == {"x": 1}

    # results should still work and keep isolation rules
    r3 = c.get(f"/results/{job_id}")
    assert r3.status_code == 200
