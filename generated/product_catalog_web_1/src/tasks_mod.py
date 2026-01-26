from __future__ import annotations

from dataclasses import dataclass, field  # noqa: F401
from typing import Dict, List, Optional


@dataclass
class User:
    id: int
    name: str


@dataclass
class Project:
    id: int
    name: str
    owner_id: int


@dataclass
class Task:
    id: int
    project_id: int
    title: str
    status: str = "todo"  # "todo" | "doing" | "done"


class TaskTracker:
    """
    Very small in-memory task tracker used as a demo for Velu.

    It is intentionally simple:
      * Users
      * Projects (owned by a user)
      * Tasks (belong to a project, have a status)

    This is a good shape for later turning into:
      * a FastAPI service
      * backed by Postgres
      * with a React / Next.js UI
    """

    def __init__(self) -> None:
        self._users: Dict[int, User] = {}
        self._projects: Dict[int, Project] = {}
        self._tasks: Dict[int, Task] = {}

        self._user_seq = 0
        self._project_seq = 0
        self._task_seq = 0

    # --------- user management ---------

    def add_user(self, name: str) -> User:
        if not name or not name.strip():
            raise ValueError("name must be non-empty")
        self._user_seq += 1
        user = User(id=self._user_seq, name=name.strip())
        self._users[user.id] = user
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    # --------- project management ---------

    def add_project(self, name: str, owner_id: int) -> Project:
        if owner_id not in self._users:
            raise ValueError(f"owner_id {owner_id} does not exist")
        if not name or not name.strip():
            raise ValueError("project name must be non-empty")
        self._project_seq += 1
        project = Project(id=self._project_seq, name=name.strip(), owner_id=owner_id)
        self._projects[project.id] = project
        return project

    def list_projects_for_user(self, owner_id: int) -> List[Project]:
        return [p for p in self._projects.values() if p.owner_id == owner_id]

    # --------- task management ---------

    def add_task(self, project_id: int, title: str, status: str = "todo") -> Task:
        if project_id not in self._projects:
            raise ValueError(f"project_id {project_id} does not exist")
        if not title or not title.strip():
            raise ValueError("task title must be non-empty")
        if status not in {"todo", "doing", "done"}:
            raise ValueError("status must be one of: todo, doing, done")

        self._task_seq += 1
        task = Task(
            id=self._task_seq,
            project_id=project_id,
            title=title.strip(),
            status=status,
        )
        self._tasks[task.id] = task
        return task

    def list_tasks(
        self,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Task]:
        tasks = list(self._tasks.values())
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def move_task(self, task_id: int, new_status: str) -> Task:
        if new_status not in {"todo", "doing", "done"}:
            raise ValueError("status must be one of: todo, doing, done")
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"task_id {task_id} not found")
        task.status = new_status
        return task


def make_demo_tracker() -> TaskTracker:
    """
    Convenience helper used by tests and future demos.
    Creates a tracker with one user, one project, and one task.
    """
    tracker = TaskTracker()
    user = tracker.add_user("Velu User")
    project = tracker.add_project("Demo Project", owner_id=user.id)
    tracker.add_task(project.id, "Initial task", status="todo")
    return tracker
