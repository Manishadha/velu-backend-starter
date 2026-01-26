from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


_users: Dict[int, User] = {}
_next_user_id: int = 1

_user_tasks: Dict[int, List[Task]] = {}
_next_task_id: int = 1


def _alloc_user_id() -> int:
    global _next_user_id
    uid = _next_user_id
    _next_user_id += 1
    return uid


def _alloc_task_id() -> int:
    global _next_task_id
    tid = _next_task_id
    _next_task_id += 1
    return tid


def _require_user(user_id: int) -> User:
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


def _require_task(user_id: int, task_id: int) -> Task:
    _require_user(user_id)
    tasks = _user_tasks.get(user_id, [])
    for t in tasks:
        if t.id == task_id:
            return t
    raise HTTPException(status_code=404, detail="task not found")


@router.get("/", response_model=list[User])
def list_users() -> list[User]:
    return list(_users.values())


@router.post("/", response_model=User, status_code=201)
def create_user(payload: UserCreate) -> User:
    uid = _alloc_user_id()
    user = User(id=uid, name=payload.name, email=payload.email)
    _users[uid] = user
    _user_tasks.setdefault(uid, [])
    return user


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int) -> User:
    return _require_user(user_id)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int) -> None:
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="not found")
    del _users[user_id]
    _user_tasks.pop(user_id, None)


@router.get("/{user_id}/tasks", response_model=list[Task])
def list_tasks(user_id: int) -> list[Task]:
    _require_user(user_id)
    return list(_user_tasks.get(user_id, []))


@router.post("/{user_id}/tasks", response_model=Task, status_code=201)
def create_task(user_id: int, payload: TaskCreate) -> Task:
    _require_user(user_id)
    tid = _alloc_task_id()
    task = Task(id=tid, title=payload.title, done=False)
    tasks = _user_tasks.setdefault(user_id, [])
    tasks.append(task)
    return task


@router.get("/{user_id}/tasks/{task_id}", response_model=Task)
def get_task(user_id: int, task_id: int) -> Task:
    return _require_task(user_id, task_id)


@router.patch("/{user_id}/tasks/{task_id}", response_model=Task)
def update_task(user_id: int, task_id: int, payload: TaskUpdate) -> Task:
    task = _require_task(user_id, task_id)
    if payload.title is not None:
        task.title = payload.title
    if payload.done is not None:
        task.done = payload.done
    return task


@router.delete("/{user_id}/tasks/{task_id}", status_code=204)
def delete_task(user_id: int, task_id: int) -> None:
    _require_task(user_id, task_id)
    tasks = _user_tasks.get(user_id, [])
    _user_tasks[user_id] = [t for t in tasks if t.id != task_id]
