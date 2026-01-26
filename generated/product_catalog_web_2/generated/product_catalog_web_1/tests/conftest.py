# tests/conftest.py
from __future__ import annotations

import os
import time
from threading import Thread

import pytest
import requests
import uvicorn


def _wait(url: str, timeout: float = 30.0) -> None:
    t0 = time.time()
    err = None
    while time.time() - t0 < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.ok and r.json().get("ok"):
                return
            err = f"HTTP {r.status_code} body={r.text[:120]}"
        except Exception as e:
            err = repr(e)
        time.sleep(0.25)
    raise RuntimeError(f"API not ready: {url} last_err={err}")


@pytest.fixture(scope="session", autouse=True)
def _api_server(tmp_path_factory):
    if os.getenv("NO_EMBEDDED_API") == "1":
        return

    # isolated env for tests
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8081")
    os.environ.setdefault("API_KEYS", "dev")
    os.environ.setdefault("TASK_DB", str(tmp_path_factory.mktemp("db") / "jobs.db"))

    from services.app_server.main import create_app

    app = create_app()
    config = uvicorn.Config(
        app,
        host=os.environ["HOST"],
        port=int(os.environ["PORT"]),
        log_level="warning",
    )
    server = uvicorn.Server(config)

    t = Thread(target=server.run, daemon=True)
    t.start()
    _wait(f"http://{os.environ['HOST']}:{os.environ['PORT']}/ready")

    yield

    server.should_exit = True
    t.join(timeout=5)
