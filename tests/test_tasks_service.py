# tests/test_tasks_service.py
from __future__ import annotations

from fastapi.testclient import TestClient

from src.tasks_service import app, TaskStatus  # type: ignore[attr-defined]


client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["service"] == "tasks"
    assert "time" in body


def test_create_project_and_list():
    # create
    resp = client.post("/projects", json={"name": "Demo Project"})
    assert resp.status_code == 200
    proj = resp.json()
    assert proj["id"] == 1
    assert proj["name"] == "Demo Project"

    # list
    resp = client.get("/projects")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any(p["name"] == "Demo Project" for p in items)


def test_create_task_and_get():
    # make sure there is at least one project
    resp = client.post("/projects", json={"name": "Tasks Project"})
    assert resp.status_code == 200
    proj = resp.json()
    pid = proj["id"]

    # create task
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "First task", "description": "demo"},
    )
    assert resp.status_code == 200
    task = resp.json()
    tid = task["id"]
    assert task["project_id"] == pid
    assert task["title"] == "First task"
    assert task["status"] == TaskStatus.todo.value

    # get task
    resp = client.get(f"/projects/{pid}/tasks/{tid}")
    assert resp.status_code == 200
    t2 = resp.json()
    assert t2["id"] == tid
    assert t2["title"] == "First task"


def test_update_task_status_and_title():
    # new project + task
    resp = client.post("/projects", json={"name": "Update Project"})
    assert resp.status_code == 200
    pid = resp.json()["id"]

    resp = client.post(f"/projects/{pid}/tasks", json={"title": "Original title"})
    assert resp.status_code == 200
    tid = resp.json()["id"]

    # update
    resp = client.patch(
        f"/projects/{pid}/tasks/{tid}",
        json={"title": "Updated title", "status": TaskStatus.in_progress.value},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated title"
    assert body["status"] == TaskStatus.in_progress.value

    # list should reflect update
    resp = client.get(f"/projects/{pid}/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert any(t["title"] == "Updated title" for t in tasks)


def test_not_found_paths():
    # project not found
    resp = client.get("/projects/9999")
    assert resp.status_code == 404

    # tasks on missing project
    resp = client.get("/projects/9999/tasks")
    assert resp.status_code == 404

    # task on missing project
    resp = client.get("/projects/9999/tasks/1")
    assert resp.status_code == 404
