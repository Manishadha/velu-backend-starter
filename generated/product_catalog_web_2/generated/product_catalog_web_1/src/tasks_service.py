# src/tasks_service.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ProjectRead(ProjectCreate):
    id: int
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None


class TaskRead(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


app = FastAPI(title="Tasks API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5178",
        "http://127.0.0.1:5179",
        "http://localhost:5173",
        "http://localhost:5174",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory store for now
_projects: Dict[int, ProjectRead] = {}
_tasks: Dict[int, TaskRead] = {}
_project_tasks: Dict[int, List[int]] = {}

_next_project_id = 1
_next_task_id = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "tasks", "time": _now().isoformat()}


@app.post("/projects", response_model=ProjectRead)
def create_project(body: ProjectCreate) -> ProjectRead:
    global _next_project_id

    proj = ProjectRead(
        id=_next_project_id,
        name=body.name,
        created_at=_now(),
    )
    _projects[proj.id] = proj
    _project_tasks.setdefault(proj.id, [])
    _next_project_id += 1
    return proj


@app.get("/projects", response_model=List[ProjectRead])
def list_projects() -> List[ProjectRead]:
    # stable order by id
    return sorted(_projects.values(), key=lambda p: p.id)


@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int) -> ProjectRead:
    proj = _projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="project_not_found")
    return proj


@app.post("/projects/{project_id}/tasks", response_model=TaskRead)
def create_task(project_id: int, body: TaskCreate) -> TaskRead:
    global _next_task_id

    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="project_not_found")

    t = TaskRead(
        id=_next_task_id,
        project_id=project_id,
        title=body.title,
        description=body.description,
        status=TaskStatus.todo,
        created_at=_now(),
        updated_at=_now(),
    )
    _tasks[t.id] = t
    _project_tasks.setdefault(project_id, []).append(t.id)
    _next_task_id += 1
    return t


@app.get("/projects/{project_id}/tasks", response_model=List[TaskRead])
def list_tasks(project_id: int) -> List[TaskRead]:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="project_not_found")

    ids = _project_tasks.get(project_id, [])
    tasks = [t for tid, t in _tasks.items() if tid in ids]
    return sorted(tasks, key=lambda t: t.id)


@app.get("/projects/{project_id}/tasks/{task_id}", response_model=TaskRead)
def get_task(project_id: int, task_id: int) -> TaskRead:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="project_not_found")

    t = _tasks.get(task_id)
    if not t or t.project_id != project_id:
        raise HTTPException(status_code=404, detail="task_not_found")
    return t


@app.patch("/projects/{project_id}/tasks/{task_id}", response_model=TaskRead)
def update_task(project_id: int, task_id: int, body: TaskUpdate) -> TaskRead:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="project_not_found")

    t = _tasks.get(task_id)
    if not t or t.project_id != project_id:
        raise HTTPException(status_code=404, detail="task_not_found")

    data = t.model_dump()
    if body.title is not None:
        data["title"] = body.title
    if body.description is not None:
        data["description"] = body.description
    if body.status is not None:
        data["status"] = body.status

    data["updated_at"] = _now()
    t2 = TaskRead(**data)
    _tasks[task_id] = t2
    return t2
