from fastapi.testclient import TestClient

from user_service import app

client = TestClient(app)


def test_user_and_task_flow() -> None:
    r = client.post("/users/", json={"name": "mani", "email": "mani@example.com"})
    assert r.status_code == 200
    user = r.json()
    uid = user["id"]

    r = client.get(f"/users/{uid}")
    assert r.status_code == 200

    r = client.post(f"/users/{uid}/tasks", json={"title": "first task"})
    assert r.status_code == 200
    task = r.json()
    tid = task["id"]
    assert task["done"] is False

    r = client.patch(f"/users/{uid}/tasks/{tid}", json={"done": True})
    assert r.status_code == 200
    task = r.json()
    assert task["done"] is True

    r = client.delete(f"/users/{uid}/tasks/{tid}")
    assert r.status_code == 204
