from __future__ import annotations
from typing import Any

# The canonical pipeline order the planner advertises to others
DEFAULT_ORDER = ("plan", "codegen", "execute", "test", "report")


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    idea = str(payload.get("idea", "demo"))
    module = str(payload.get("module", "hello_mod"))

    plan_text = f"{idea} via {module}"
    extra: dict[str, Any] = {}

    idea_norm = idea.lower().strip()
    module_norm = module.strip()

    if idea_norm.startswith("build api") and module_norm == "user_service":
        extra = {
            "summary": "CRUD API for users and tasks",
            "steps": [
                "Define in-memory models for users and tasks",
                "Expose /users CRUD endpoints",
                "Expose /users/{user_id}/tasks CRUD endpoints",
                "Return Pydantic models from all handlers",
            ],
            "endpoints": [
                {"method": "POST", "path": "/users/", "desc": "Create user"},
                {"method": "GET", "path": "/users/", "desc": "List users"},
                {"method": "GET", "path": "/users/{user_id}", "desc": "Get user"},
                {"method": "DELETE", "path": "/users/{user_id}", "desc": "Delete user"},
                {
                    "method": "GET",
                    "path": "/users/{user_id}/tasks",
                    "desc": "List tasks for user",
                },
                {
                    "method": "POST",
                    "path": "/users/{user_id}/tasks",
                    "desc": "Create task for user",
                },
                {
                    "method": "GET",
                    "path": "/users/{user_id}/tasks/{task_id}",
                    "desc": "Get task",
                },
                {
                    "method": "PATCH",
                    "path": "/users/{user_id}/tasks/{task_id}",
                    "desc": "Update task title or done flag",
                },
                {
                    "method": "DELETE",
                    "path": "/users/{user_id}/tasks/{task_id}",
                    "desc": "Delete task",
                },
            ],
        }

    result: dict[str, Any] = {"ok": True, "plan": plan_text}
    result.update(extra)
    return result
