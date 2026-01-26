from tasks_mod import TaskTracker, make_demo_tracker


def test_can_create_user_and_project():
    tracker = TaskTracker()
    user = tracker.add_user("Alice")
    project = tracker.add_project("My Project", owner_id=user.id)

    assert user.id == 1
    assert project.id == 1
    assert project.owner_id == user.id
    assert tracker.get_user(user.id) is not None


def test_cannot_create_project_for_missing_user():
    tracker = TaskTracker()
    try:
        tracker.add_project("Orphan", owner_id=999)
    except ValueError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing owner")


def test_add_and_list_tasks():
    tracker = TaskTracker()
    user = tracker.add_user("Bob")
    project = tracker.add_project("Tasks", owner_id=user.id)

    t1 = tracker.add_task(project.id, "Task one", status="todo")
    t2 = tracker.add_task(project.id, "Task two", status="doing")

    all_tasks = tracker.list_tasks(project_id=project.id)
    assert {t.id for t in all_tasks} == {t1.id, t2.id}

    todo = tracker.list_tasks(project_id=project.id, status="todo")
    assert [t.id for t in todo] == [t1.id]


def test_move_task_between_statuses():
    tracker = make_demo_tracker()
    tasks = tracker.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]

    tracker.move_task(task.id, "doing")
    doing = tracker.list_tasks(status="doing")
    assert [t.id for t in doing] == [task.id]

    tracker.move_task(task.id, "done")
    done = tracker.list_tasks(status="done")
    assert [t.id for t in done] == [task.id]


def test_make_demo_tracker_has_initial_data():
    tracker = make_demo_tracker()
    users_projects_tasks = (
        len(tracker._users),
        len(tracker._projects),
        len(tracker._tasks),
    )
    assert users_projects_tasks == (1, 1, 1)
