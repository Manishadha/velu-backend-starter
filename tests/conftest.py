# tests/conftest.py
from __future__ import annotations

import os
import time
from threading import Thread
from pathlib import Path  # noqa: F401

import pytest
import requests
import uvicorn
import sys  # noqa: F401
import socket

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

# ---------------------------------------------------------------------
# CRITICAL: set these at import time (collection-time), not in fixtures.
# This fixes tests that assert env vars during import/collection.
# ---------------------------------------------------------------------
os.environ.setdefault("ENV", "test")

# Make sure platform admin key exists for org bootstrap tests
# Use something long-ish so any "prod-ish" checks won't reject it.
os.environ.setdefault("TEST_PLATFORM_ADMIN_KEY", "k_test_platform_admin_123456789012345678901234")
os.environ.setdefault("VELU_ADMIN_KEY", os.environ["TEST_PLATFORM_ADMIN_KEY"])

# Default to permissive local/dev mode unless a test overrides.
# "dev" is treated as "no auth configured" in services/app_server/auth.py
os.environ.setdefault("VELU_API_KEYS_BACKEND", "env")
os.environ.setdefault("API_KEYS", "dev")

# Default jobs backend for unit/integration tests running in-process
os.environ.setdefault("VELU_JOBS_BACKEND", "sqlite")

# Disable DB lookups by default (postgres tests can enable explicitly)
os.environ.setdefault("VELU_TEST_DB_LOOKUP", "0")


def _free_port() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return str(s.getsockname()[1])


def project_root() -> Path:
    """
    Return the root of the Velu project (repo root).
    Many tests use this to build absolute paths.
    """
    return Path(__file__).resolve().parent.parent


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


@pytest.fixture(autouse=True)
def _backend_toggle_per_test(request, monkeypatch):
    """
    Per-test backend toggle.

    Default:
      - sqlite jobs backend
      - env api keys backend (API_KEYS=dev => permissive)
      - no DB lookups (VELU_TEST_DB_LOOKUP=0)

    For tests whose nodeid contains "postgres":
      - postgres jobs backend
      - postgres api keys backend
      - allow DB lookups (VELU_TEST_DB_LOOKUP=1)
    """
    nodeid = request.node.nodeid.lower()
    if "postgres" in nodeid:
        monkeypatch.setenv("VELU_JOBS_BACKEND", "postgres")
        monkeypatch.setenv("VELU_API_KEYS_BACKEND", "postgres")
        monkeypatch.setenv("VELU_TEST_DB_LOOKUP", "1")
    else:
        monkeypatch.setenv("VELU_JOBS_BACKEND", "sqlite")
        monkeypatch.setenv("VELU_API_KEYS_BACKEND", "env")
        monkeypatch.setenv("VELU_TEST_DB_LOOKUP", "0")
        monkeypatch.setenv("API_KEYS", "dev")


@pytest.fixture(scope="session", autouse=True)
def _api_server(tmp_path_factory):
    if os.getenv("NO_EMBEDDED_API") == "1":
        yield
        return

    # isolated env for tests
    os.environ.setdefault("VELU_TESTING", "1")

    # Ensure host/port exist (some setups don’t set them)
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", _free_port())

    base = tmp_path_factory.mktemp("velu_data")
    os.environ.setdefault("TASK_DB", str(base / "jobs.db"))
    os.environ.setdefault("BLUEPRINT_DB", str(base / "blueprints.db"))

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
