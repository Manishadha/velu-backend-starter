# src/user_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class UserIn(BaseModel):
    name: str
    email: str


class User(UserIn):
    id: int


class TaskIn(BaseModel):
    title: str


class Task(TaskIn):
    id: int
    done: bool = False


class TaskUpdate(BaseModel):
    done: bool


_users: dict[int, User] = {}
_tasks: dict[int, dict[int, Task]] = {}
_next_user_id = 1
_next_task_id = 1


@app.post("/users/", response_model=User)
def create_user(user: UserIn) -> User:
    global _next_user_id
    uid = _next_user_id
    _next_user_id += 1
    db_user = User(id=uid, **user.model_dump())
    _users[uid] = db_user
    return db_user


@app.get("/users/", response_model=list[User])
def list_users() -> list[User]:
    return list(_users.values())


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int) -> User:
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int) -> None:
    if user_id in _users:
        del _users[user_id]
        _tasks.pop(user_id, None)
    return None


@app.post("/users/{user_id}/tasks", response_model=Task)
def create_task(user_id: int, task: TaskIn) -> Task:
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="user not found")
    global _next_task_id
    tid = _next_task_id
    _next_task_id += 1
    user_tasks = _tasks.setdefault(user_id, {})
    db_task = Task(id=tid, done=False, **task.model_dump())
    user_tasks[tid] = db_task
    return db_task


@app.get("/users/{user_id}/tasks", response_model=list[Task])
def list_tasks(user_id: int) -> list[Task]:
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="user not found")
    return list(_tasks.get(user_id, {}).values())


@app.get("/users/{user_id}/tasks/{task_id}", response_model=Task)
def get_task(user_id: int, task_id: int) -> Task:
    user_tasks = _tasks.get(user_id)
    if not user_tasks or task_id not in user_tasks:
        raise HTTPException(status_code=404, detail="task not found")
    return user_tasks[task_id]


@app.patch("/users/{user_id}/tasks/{task_id}", response_model=Task)
def update_task(user_id: int, task_id: int, patch: TaskUpdate) -> Task:
    user_tasks = _tasks.get(user_id)
    if not user_tasks or task_id not in user_tasks:
        raise HTTPException(status_code=404, detail="task not found")
    task = user_tasks[task_id]
    task.done = patch.done
    user_tasks[task_id] = task
    return task


@app.delete("/users/{user_id}/tasks/{task_id}", status_code=204)
def delete_task(user_id: int, task_id: int) -> None:
    user_tasks = _tasks.get(user_id)
    if user_tasks and task_id in user_tasks:
        del user_tasks[task_id]
    return None
