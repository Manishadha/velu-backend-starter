from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app
from services.queue import sqlite_queue as q  # type: ignore


client = TestClient(app)


def test_assistant_intake_can_enqueue_pipeline_job() -> None:
    body = {
        "company": {"name": "Acme Travel"},
        "product": {
            "type": "saas",
            "goal": "internal_tool",
            "locales": ["en", "fr"],
        },
        "idea": "tableau de bord pour mon équipe",
        "run_pipeline": True,
    }

    resp = client.post("/v1/assistant/intake", json=body)
    assert resp.status_code == 200

    data = resp.json()
    assert data["ok"] is True

    jid = data.get("pipeline_job_id")
    assert isinstance(jid, int)

    job = q.load(int(jid))
    assert job is not None
    assert job["task"] == "pipeline"

    payload = job["payload"]
    assert payload["idea"] == body["idea"]
    assert payload["module"] == data["pipeline_module"]
    assert payload["locales"] == ["en", "fr"]
