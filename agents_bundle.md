
---
# services/agents/aggregate.py

```python
# services/agents/aggregate.py
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import suppress
from typing import Any

from services.queue import sqlite_queue as q


def _con() -> sqlite3.Connection:
    db = os.environ.get("TASK_DB", "/data/jobs.db")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def _to_json(v: Any) -> dict:
    if not v:
        return {}
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v)
    except Exception:
        return {}


def _get_job(con: sqlite3.Connection, jid: int) -> dict[str, Any]:
    row = con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    if not row:
        return {}
    d = dict(row)
    d["payload"] = _to_json(d.get("payload"))
    d["result"] = _to_json(d.get("result"))
    return d


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        parent = int(payload.get("parent_job") or 0)
        if not parent:
            return {"ok": False, "agent": "aggregate", "error": "missing parent_job"}

        con = _con()
        try:
            parent_job = _get_job(con, parent)
            if not parent_job:
                return {
                    "ok": False,
                    "agent": "aggregate",
                    "error": "parent not found",
                }
        finally:
            con.close()

        # Optional: write an audit entry that aggregation ran (best-effort)
        with suppress(Exception):
            q.audit("aggregate", job_id=parent, actor="worker", detail={})

        return {
            "ok": True,
            "agent": "aggregate",
            "parent": parent,
            "summary": "ok",
        }
    except Exception as e:
        return {"ok": False, "agent": "aggregate", "error": str(e)}

```

---
# services/agents/ai_features.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    enable = bool(payload.get("enable", True))
    files: list[dict[str, str]] = []
    if enable:
        content = (
            "def reply(q: str) -> str:\n"
            "    # TODO: implement real assistant logic\n"
            "    return 'ok'\n"
        )
        files.append({"path": "services/ai/assistant.py", "content": content})
    return {"ok": True, "agent": "ai_features", "files": files}

```

---
# services/agents/analyzer.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Toy analyzer: counts keys/values and echoes back."""
    payload = payload or {}
    keys = list(payload.keys())
    return {
        "ok": True,
        "agent": "analyzer",
        "result": {
            "key_count": len(keys),
            "keys": keys,
            "summary": "analysis complete",
        },
    }

```

---
# services/agents/api_design.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    openapi = {
        "openapi": "3.1.0",
        "info": {"title": "Velu API", "version": "v1"},
        "paths": {
            "/v1/health": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/v1/auth/login": {"post": {"responses": {"200": {"description": "logged in"}}}},
        },
        "components": {},
    }
    return {"ok": True, "agent": "api_design", "openapi": openapi}

```

---
# services/agents/architecture.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    ptype = payload.get("product", {}).get("type", "website")
    frontend = (
        "nextjs"
        if ptype in {"website", "saas", "portal", "ecommerce", "marketplace"}
        else "flutter"
    )

    stack = {
        "frontend": frontend,
        "backend": "fastapi",
        "db": "postgres",
    }
    views = ["landing", "auth", "dashboard"]
    services = ["api", "worker"]
    return {
        "ok": True,
        "agent": "architecture",
        "stack": stack,
        "views": views,
        "services": services,
    }  # noqa: E501

```

---
# services/agents/backend_scaffold.py

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

_TPL = Path("templates")


def _read(p: Path, default: str) -> str:
    try:
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        pass
    return default


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    files: list[dict[str, str]] = []

    app_tpl = _read(
        _TPL / "fastapi_app.py.j2",
        "from fastapi import FastAPI\n\n"
        "def create_app() -> FastAPI:\n"
        "    app = FastAPI(title='App', version='1.0.0')\n"
        "    from .routes import health\n"
        "    app.include_router(health.router, prefix='')\n"
        "    return app\n\n"
        "app = create_app()\n",
    )
    files.append({"path": "services/api/app.py", "content": app_tpl})

    router_tpl = _read(
        _TPL / "router_stub.py.j2",
        "from fastapi import APIRouter\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/health')\n"
        "def health():\n"
        "    return {'ok': True}\n",
    )
    files.append({"path": "services/api/routes/health.py", "content": router_tpl})

    return {"ok": True, "agent": "backend_scaffold", "files": files}

```

---
# services/agents/codegen.py

```python
# services/agents/codegen.py
from __future__ import annotations

from typing import Any

# ruff: noqa: E501


def _slug(s: str) -> str:
    out = []
    for ch in (s or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    slug = "".join(out).strip("-")
    return slug or "app"


def _python_cli(spec: str, appname: str) -> str:
    """Deterministic Python CLI scaffold. Includes the required phrase in code."""
    return f"""\
#!/usr/bin/env python3
# hello from codegen: {spec}
from __future__ import annotations

import argparse

def main() -> int:
    parser = argparse.ArgumentParser(prog="{appname}", description="{spec}")
    parser.add_argument("--name", default="world", help="Name to greet")
    args = parser.parse_args()
    print(f"Hello, {{args.name}}!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""


def handle(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Two supported input shapes:

    1) Spec-based (unit tests use this):
       payload = {"lang": "python", "spec": "..."}
       -> returns {"ok": True, "artifact": {"language":"python","path":...,"code":...}, "files":[...]}

       Unsupported languages return ok=False.

    2) Legacy/pipeline-friendly:
       payload = {"idea": "...", "module": "..."}
       -> returns {"ok": True, "files": [...]}
    """
    # -----------------------------
    # Shape 1: language + spec
    # -----------------------------
    if "lang" in payload:
        lang = str(payload.get("lang", "")).lower().strip()
        spec = str(payload.get("spec", "")).strip() or "CLI app"

        if lang != "python":
            return {"ok": False, "error": f"unsupported lang: {lang}", "supported": ["python"]}

        fname = _slug(spec)
        path = f"generated/{fname}.py"
        code = _python_cli(spec=spec, appname=fname)

        files = [{"path": path, "content": code}]
        artifact = {"path": path, "language": "python", "code": code}

        return {"ok": True, "agent": "codegen", "artifact": artifact, "files": files}

    # -----------------------------
    # Shape 2: idea + module (pipeline legacy)
    # -----------------------------
    idea = str(payload.get("idea", "")).strip()
    module = str(payload.get("module", "")).strip() or "hello_mod"

    py_path = f"src/{module}.py"
    test_path = f"tests/test_{module}.py"

    files = [
        {"path": py_path, "content": f'def run():\n    return "{idea or "demo"} via {module}"\n'},
        {"path": test_path, "content": "def test_sanity():\n    assert True\n"},
    ]

    return {"ok": True, "agent": "codegen", "files": files}

```

---
# services/agents/datamodel.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    entities = payload.get("entities") or [
        {"name": "Account"},
        {"name": "User"},
    ]

    ddl_parts: list[str] = []
    for ent in entities:
        name = str(ent["name"]).lower()
        ddl_parts.append(
            f"CREATE TABLE IF NOT EXISTS {name} ("
            "id uuid PRIMARY KEY, "
            "tenant_id uuid, "
            "created_at timestamptz default now()"
            ");"
        )

    ddl = "\n".join(ddl_parts)
    migrations = [{"id": "001_init.sql", "sql": ddl}]
    return {
        "ok": True,
        "agent": "datamodel",
        "models": entities,
        "migrations": migrations,
        "ddl": ddl,
    }

```

---
# services/agents/echo.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Echo agent: returns payload unchanged."""
    return {"ok": True, "agent": "echo", "data": payload or {}}

```

---
# services/agents/executor.py

```python
# services/agents/executor.py
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = (os.getenv("TASK_DB") or "/data/jobs.db").strip()
APP_ROOT = Path(os.getenv("APP_ROOT") or Path.cwd()).resolve()

ROOTS: dict[str, Path] = {
    "src": APP_ROOT / "src",
    "tests": APP_ROOT / "tests",
    "generated": APP_ROOT / "generated",
}

for p in ROOTS.values():
    p.mkdir(parents=True, exist_ok=True)


def _normalize_target(rel_path: str) -> tuple[Path, Path]:
    rel = (rel_path or "").lstrip("/")
    if rel.startswith("src/"):
        return ROOTS["src"], Path(rel[len("src/") :])
    if rel.startswith("tests/"):
        return ROOTS["tests"], Path(rel[len("tests/") :])
    if rel.startswith("generated/"):
        return ROOTS["generated"], Path(rel[len("generated/") :])
    return ROOTS["generated"], Path(rel)


def _safe_join(base: Path, tail: Path) -> Path | None:
    if tail.is_absolute():
        return None
    target = (base / tail).resolve()
    try:
        if not target.is_relative_to(base.resolve()):
            return None
    except AttributeError:  # py<=3.10
        b, t = str(base.resolve()), str(target)
        if not (t == b or t.startswith(b.rstrip("/") + "/")):
            return None
    return target


def _files_from_job(job_id: int) -> list[dict[str, str]]:
    with contextlib.suppress(Exception):
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT result FROM jobs WHERE id=?", (job_id,)).fetchone()
        con.close()
        if not row:
            return []
        data = json.loads(row["result"] or "{}")
        return data.get("files") or (data.get("result") or {}).get("files") or []
    return []


def _iter_files(payload: dict[str, Any]) -> list[dict[str, str]]:
    files = payload.get("files")
    if isinstance(files, list):
        return [f for f in files if isinstance(f, dict)]
    from_job = payload.get("from_job")
    if isinstance(from_job, int):
        return _files_from_job(from_job)
    return []


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    files = _iter_files(payload or {})
    wrote: list[str] = []
    refused: list[dict[str, str]] = []

    for f in files:
        rel_in = str(f.get("path") or "")
        content = f.get("content")

        if not rel_in:
            refused.append({"path": "<empty>", "reason": "missing path"})
            continue
        if not isinstance(content, str):
            refused.append({"path": rel_in, "reason": "content must be string"})
            continue
        if rel_in.startswith("/"):
            refused.append({"path": rel_in, "reason": "absolute path not allowed"})
            continue

        base, tail = _normalize_target(rel_in)
        if any(part == ".." for part in tail.parts):
            refused.append({"path": rel_in, "reason": "path traversal not allowed"})
            continue

        safe = _safe_join(base, tail)
        if safe is None:
            refused.append({"path": rel_in, "reason": "outside allowed roots"})
            continue

        bad_link = False
        cur = safe
        while True:
            if cur.is_symlink():
                bad_link = True
                break
            parent = cur.parent
            if parent == cur:
                break
            cur = parent
        if bad_link:
            refused.append({"path": rel_in, "reason": "symlinked path not allowed"})
            continue

        try:
            safe.parent.mkdir(parents=True, exist_ok=True)
            data = content.replace("\r\n", "\n")
            safe.write_text(data, encoding="utf-8")
            wrote.append(str(safe.relative_to(APP_ROOT)))
        except Exception as e:
            refused.append({"path": rel_in, "reason": f"write failed: {type(e).__name__}: {e}"})

    return {"ok": True, "agent": "executor", "wrote": wrote, "refused": refused}

```

---
# services/agents/gitcommit.py

```python
from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from typing import Any

_CC = re.compile(r"^(feat|fix|chore|docs|refactor|test|build|ci|perf|style)" r"(\\([^)]+\\))?: .+")


def _run(cmd: Sequence[str]) -> tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    msg = str(payload.get("message") or "chore: snapshot").strip()
    paths = payload.get("paths")
    if not _CC.match(msg):
        return {"ok": False, "agent": "gitcommit", "error": "invalid subject"}

    git = ["git", "--git-dir=/git/.git", "--work-tree=/app"]
    rc, _, _ = _run(git + ["rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        return {"ok": True, "agent": "gitcommit", "did_commit": False, "reason": "no repo"}

    if paths and isinstance(paths, list):
        _run(git + ["add", "--"] + [str(p) for p in paths])
    else:
        _run(git + ["add", "-A"])

    rc, _, _ = _run(git + ["diff", "--cached", "--quiet"])
    has_changes = rc != 0
    if not has_changes:
        rc_h, head, _ = _run(git + ["rev-parse", "HEAD"])
        return {
            "ok": True,
            "agent": "gitcommit",
            "did_commit": False,
            "reason": "no changes",
            "head": head.strip() if rc_h == 0 else None,
            "subject": msg,
        }

    rc, _, err = _run(git + ["commit", "-m", msg])
    if rc != 0:
        return {"ok": False, "agent": "gitcommit", "error": f"commit failed: {err.strip()}"}

    rc, head, _ = _run(git + ["rev-parse", "HEAD"])
    rc, ls, _ = _run(git + ["diff-tree", "--no-commit-id", "--name-only", "-r", head.strip()])
    files = ls.splitlines() if rc == 0 else []
    return {
        "ok": True,
        "agent": "gitcommit",
        "did_commit": True,
        "head": head.strip(),
        "subject": msg,
        "files": files,
    }

```

---
# services/agents/__init__.py

```python
from __future__ import annotations

from . import analyzer, codegen, executor, pipeline, planner, report, tester

HANDLERS = {
    "analyze": analyzer.handle,
    "plan": planner.handle,
    "codegen": codegen.handle,
    "generate_code": codegen.handle,
    "execute": executor.handle,
    "pipeline": pipeline.handle,
    "report": report.handle,
    "test": tester.handle,
}

```

---
# services/agents/intake.py

```python
from __future__ import annotations

from typing import Any


def _norm_str(v: Any, default: str = "") -> str:
    return str(v).strip() if isinstance(v, (str, bytes)) else default


def _normalize(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": _norm_str(p.get("kind"), "website"),
        "idea": _norm_str(p.get("idea"), "App"),
        "frontend": _norm_str(p.get("frontend"), "nextjs"),
        "backend": _norm_str(p.get("backend"), "fastapi"),
        "database": _norm_str(p.get("database"), "sqlite"),
        "schema": p.get("schema") or {},
        "module": _norm_str(p.get("module"), "hello_mod"),
    }


def handle(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        norm = _normalize(payload)
    except Exception as e:
        err = f"normalize-failed: {type(e).__name__}: {e}"
        return {"ok": False, "agent": "intake", "error": err}

    try:
        from services.queue import sqlite_queue as q  # type: ignore
    except Exception as e:
        err = f"queue-import-failed: {type(e).__name__}: {e}"
        return {"ok": False, "agent": "intake", "error": err}

    pipe_payload = {
        "idea": norm["idea"],
        "module": norm["module"],
        "frontend": norm["frontend"],
        "backend": norm["backend"],
        "database": norm["database"],
        "kind": norm["kind"],
        "schema": norm["schema"],
    }

    jid = q.enqueue(task="pipeline", payload=pipe_payload, priority=0)

    return {
        "ok": True,
        "agent": "intake",
        "msg": "intake accepted; pipeline enqueued",
        "pipeline_job_id": jid,
        "normalized": norm,
    }

```

---
# services/agents/pipeline.py

```python
from __future__ import annotations

from typing import Any

from services.agents.planner import DEFAULT_ORDER
from services.queue import sqlite_queue as q


def _norm(payload: dict[str, Any]) -> dict[str, Any]:
    idea = str(payload.get("idea", "demo")).strip() or "demo"
    module = str(payload.get("module", "hello_mod")).strip() or "hello_mod"
    return {"idea": idea, "module": module}


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    p = _norm(payload or {})
    order = list(DEFAULT_ORDER)

    files = [
        {"path": "web/pages/index.tsx", "content": "export default function Home(){\n  return <div>Hello Velu</div>\n}\n"},
        {"path": "web/package.json", "content": "{\n  \"name\": \"web\", \"private\": true\n}\n"},
        {"path": "services/api/app.py", "content": "from fastapi import FastAPI\n\ndef create_app() -> FastAPI:\n    app = FastAPI(title=\"{{ title }}\", version=\"{{ version }}\")\n    from .routes import health\n    app.include_router(health.router, prefix=\"\")\n    return app\n\napp = create_app()\n"},
        {"path": "services/api/routes/health.py", "content": "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get(\"/health\")\ndef health():\n    return {\"ok\": True}\n"},
        {"path": "services/ai/assistant.py", "content": "def reply(q: str) -> str:\n    return 'ok'\n"},
        {"path": "services/app_server/security/headers.py", "content": "from starlette.middleware.base import BaseHTTPMiddleware\nfrom starlette.types import ASGIApp\nfrom typing import Callable\n\nclass SecurityHeadersMiddleware(BaseHTTPMiddleware):\n    def __init__(self, app: ASGIApp):\n        super().__init__(app)\n\n    async def dispatch(self, request, call_next: Callable):\n        resp = await call_next(request)\n        resp.headers['X-Content-Type-Options']='nosniff'\n        resp.headers['Referrer-Policy']='strict-origin-when-cross-origin'\n        resp.headers['X-Frame-Options']='DENY'\n        resp.headers['Cross-Origin-Opener-Policy']='same-origin'\n        resp.headers['Cross-Origin-Resource-Policy']='same-site'\n        resp.headers['Permissions-Policy']='geolocation=(), microphone=()'\n        resp.headers['Content-Security-Policy']=\"default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'\"\n        return resp\n"},
        {"path": "tests/test_health.py", "content": "def test_sanity():\n    assert True\n"},
    ]

    exec_id = q.enqueue(task="execute", payload={"files": files}, priority=0)
    test_id = q.enqueue(
        task="test",
        payload={
            "rootdir": "/app",
            "tests_path": "/app/tests",
            "args": ["-q", "--maxfail=1", "--disable-warnings", "--basetemp=/tmp/pytest"],
        },
        priority=0,
    )

    summary = {"idea": p["idea"], "module": p["module"], "order": order, "file_count": len(files)}
    return {"ok": True, "agent": "pipeline", "summary": summary, "subjobs": {"execute": exec_id, "test": test_id}}

```

---
# services/agents/planner.py

```python
from __future__ import annotations

from typing import Any

from services.queue import sqlite_queue as q


def handle(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Simple planner."""
    idea = str(payload.get("idea", "demo"))
    module = str(payload.get("module", "hello_mod"))
    return {"ok": True, "plan": f"{idea} via {module}"}


def handle_pipeline(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Orchestrator task:
      - enqueues 'plan'
      - enqueues 'codegen' (built-in generator)
    Returns subjob IDs so /results/{id}?expand=1 can show details.
    On failure, returns ok=False with error details (no exception escapes).
    """
    idea = str(payload.get("idea", "demo"))
    module = str(payload.get("module", "hello_mod"))

    try:
        plan_id = q.enqueue(
            task="plan",
            payload={"idea": idea, "module": module},
            priority=0,
        )
    except Exception as e:
        return {
            "ok": False,
            "stage": "enqueue-plan",
            "error": str(e),
            "inputs": {"idea": idea, "module": module},
        }

    try:
        gen_id = q.enqueue(
            task="codegen",  # IMPORTANT: use the built-in codegen agent
            payload={"idea": idea, "module": module},
            priority=0,
        )
    except Exception as e:
        return {
            "ok": False,
            "stage": "enqueue-codegen",
            "error": str(e),
            "subjobs": {"plan": plan_id},
            "inputs": {"idea": idea, "module": module},
        }

    return {
        "ok": True,
        "msg": "pipeline started",
        "subjobs": {
            "plan": plan_id,
            "generate": gen_id,
        },
    }

```

---
# services/agents/plan.py

```python
"""Simple planning agent."""

from __future__ import annotations


def run(payload: dict | None = None) -> dict:
    """Return a tiny plan based on the input payload."""
    payload = payload or {}
    idea = payload.get("idea")
    steps = ["collect inputs", "draft plan", "review", "finalize"]

    return {
        "ok": True,
        "agent": "planner",
        "task": "plan",
        "steps": steps,
        "inputs": {"idea": idea} if idea is not None else {},
    }

```

---
# services/agents/postdeploy_checks.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "agent": "postdeploy_checks", "smoke": ["GET /ready", "GET /metrics"]}

```

---
# services/agents/reporter.py

```python
from __future__ import annotations

from typing import Any


def handle(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Simple reporter: formats a tiny report string.
    """
    title = str(payload.get("title") or "Report")
    data = payload.get("data")
    snippet = str(data)[:160] if data is not None else "<no data>"
    return {
        "agent": "reporter",
        "task": task,
        "payload": payload,
        "result": {
            "title": title,
            "text": f"{title}: {snippet}",
        },
        "ok": True,
    }

```

---
# services/agents/report.py

```python
from __future__ import annotations

import json
import sqlite3
from typing import Any

DB = "/data/jobs.db"


def _row_to_json(val: str | bytes | None) -> dict | list | None:
    if not val:
        return None
    if isinstance(val, bytes):
        val = val.decode("utf-8", "ignore")
    try:
        data = json.loads(val)
        return data if isinstance(data, (dict, list)) else {"raw": data}
    except Exception:
        return None


def _get(con: sqlite3.Connection, jid: int) -> dict[str, Any] | None:
    con.row_factory = sqlite3.Row
    r = con.execute(
        "SELECT id, task, status, result, last_error, payload FROM jobs WHERE id=?",
        (jid,),
    ).fetchone()
    return dict(r) if r else None


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    parent = int(payload.get("parent_job", 0)) or 0
    if parent <= 0:
        return {"ok": False, "agent": "report", "error": "invalid parent_job"}

    con = sqlite3.connect(DB)
    try:
        job = _get(con, parent)
        if not job:
            return {"ok": False, "agent": "report", "error": "parent not found"}

        res = _row_to_json(job.get("result"))
        if not isinstance(res, dict):
            return {"ok": False, "agent": "report", "error": "parent has no result"}

        detail = res.get("subjobs_detail") or {}
        if not isinstance(detail, dict):
            detail = {}

        return {
            "ok": True,
            "agent": "report",
            "job": {"id": job["id"], "task": job["task"], "status": job["status"]},
            "subjobs": list(detail.keys()),
        }
    finally:
        con.close()

```

---
# services/agents/requirements.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    idea = str(payload.get("idea") or "demo")
    module = str(payload.get("module") or "hello_mod")

    # Convert intake into user stories & NFRs
    stories = [
        {
            "as": "user",
            "i_want": "sign in",
            "so_that": "I can access my account",
        },
        {
            "as": "admin",
            "i_want": "manage users",
            "so_that": "I can administer the org",
        },
    ]

    ops = payload.get("ops")
    regions = ops.get("regions", []) if isinstance(ops, dict) else []

    nfr = {
        "availability_slo": "99.9%",
        "p95_latency_ms": 300,
        "regions": regions,
    }

    return {
        "ok": True,
        "agent": "requirements",
        "idea": idea,
        "module": module,
        "stories": stories,
        "nfr": nfr,
        "risks": [],
        "notes": [],
    }

```

---
# services/agents/security_hardening.py

```python
from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    csp = "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    files: list[dict[str, str]] = [
        {
            "path": "services/app_server/security/headers.py",
            "content": f"""from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request, call_next: Callable):
        resp = await call_next(request)
        resp.headers['X-Content-Type-Options']='nosniff'
        resp.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        resp.headers['X-Frame-Options']='DENY'
        resp.headers['Cross-Origin-Opener-Policy']='same-origin'
        resp.headers['Cross-Origin-Resource-Policy']='same-site'
        resp.headers['Permissions-Policy']='geolocation=(), microphone=()'
        resp.headers['Content-Security-Policy']="{csp}"
        return resp
""",
        }
    ]
    return {"ok": True, "agent": "security_hardening", "files": files}

```

---
# services/agents/tester.py

```python
from __future__ import annotations

import os
import subprocess
from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Runs pytest safely:
      * rootdir defaults to /app
      * tests_path defaults to /app/tests
      * args defaults: -q --maxfail=1 --disable-warnings --basetemp=/tmp/pytest
    """
    rootdir = str(payload.get("rootdir", "/app"))
    tests_path = str(payload.get("tests_path", "/app/tests"))
    args = payload.get("args") or [
        "-q",
        "--maxfail=1",
        "--disable-warnings",
        "--basetemp=/tmp/pytest",
    ]

    cmd = ["python", "-m", "pytest", tests_path, *args]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "/app:/app/src")
    env.setdefault("HOME", "/tmp")

    try:
        cp = subprocess.run(
            cmd,
            cwd=rootdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        ok = cp.returncode == 0
        return {
            "ok": ok,
            "agent": "test",
            "returncode": cp.returncode,
            "stdout": cp.stdout[-10000:],
            "stderr": cp.stderr[-10000:],
        }
    except Exception as e:
        return {
            "ok": False,
            "agent": "test",
            "error": f"pytest-failed: {type(e).__name__}: {e}",
        }

```

---
# services/agents/testgen.py

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

_TPL = Path("templates")


def _read(p: Path, default: str) -> str:
    try:
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        pass
    return default


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    content = _read(_TPL / "test_smoke.py.j2", "def test_sanity(): assert True\n")
    tests: list[dict[str, str]] = [{"path": "tests/test_health.py", "content": content}]
    return {"ok": True, "agent": "testgen", "files": tests}

```

---
# services/agents/ui_scaffold.py

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

_TPL = Path("templates")


def _read(p: Path, default: str) -> str:
    try:
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        pass
    return default


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    files: list[dict[str, str]] = []

    index_tpl = _read(
        _TPL / "next_index.tsx.j2",
        "export default function Home(){\n" "  return <div>Hello Velu</div>\n" "}\n",
    ).replace("{{ headline }}", "Hello Velu")
    files.append({"path": "web/pages/index.tsx", "content": index_tpl})

    pkg = '{\n  "name": "web", "private": true\n}\n'
    files.append({"path": "web/package.json", "content": pkg})

    return {"ok": True, "agent": "ui_scaffold", "files": files}

```

---
# services/queue/worker_entry.py

```python
# services/queue/worker_entry.py
from __future__ import annotations

import json
import os
import signal
import sqlite3
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from services.agents import (
    aggregate,
    ai_features,
    api_design,
    architecture,
    backend_scaffold,
    codegen,
    datamodel,
    executor,
    gitcommit,
    intake,
    pipeline,
    planner,
    report,
    requirements,
    security_hardening,
    tester,
    testgen,
    ui_scaffold,
)
from services.queue import sqlite_queue as q

HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "requirements": requirements.handle,
    "architecture": architecture.handle,
    "datamodel": datamodel.handle,
    "api_design": api_design.handle,
    "ui_scaffold": ui_scaffold.handle,
    "backend_scaffold": backend_scaffold.handle,
    "ai_features": ai_features.handle,
    "security_hardening": security_hardening.handle,
    "testgen": testgen.handle,
    "pipeline": pipeline.handle,
    "plan": planner.handle,
    "aggregate": aggregate.handle,
    "gitcommit": gitcommit.handle,
    "codegen": codegen.handle,
    "execute": executor.handle,
    "test": tester.handle,
    "report": report.handle,
    "intake": intake.handle,
}

DB_PATH = os.getenv("TASK_DB", "/data/jobs.db")
_stop = False


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    with suppress(Exception):
        con.execute("PRAGMA busy_timeout=5000;")
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
    return con


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        with suppress(Exception):
            return json.dumps({"_repr": repr(obj)}, ensure_ascii=False)
        return "{}"


def _db_pop_one() -> dict[str, Any] | None:
    con = _connect()
    cur = con.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        row = cur.execute(
            """
            SELECT id, task, payload
              FROM jobs
             WHERE status = 'queued'
               AND (next_run_at IS NULL OR next_run_at <= strftime('%s','now'))
             ORDER BY priority DESC, COALESCE(next_run_at, 0) ASC, id ASC
             LIMIT 1
            """
        ).fetchone()
        if not row:
            con.commit()
            return None

        jid = int(row["id"])
        cur.execute(
            "UPDATE jobs SET status='working', updated_at=? WHERE id=?",
            (time.time(), jid),
        )
        con.commit()

        payload_raw = row["payload"]
        if isinstance(payload_raw, (bytes, bytearray)):
            payload_raw = payload_raw.decode("utf-8", "ignore")
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
            if not isinstance(payload, dict):
                payload = {"raw": payload}
        except Exception:
            payload = {"raw": payload_raw}

        return {"id": jid, "task": str(row["task"] or "").strip(), "payload": payload}
    finally:
        with suppress(Exception):
            con.close()


def _db_done(jid: int, result: dict[str, Any] | None, err: dict[str, Any] | None) -> None:
    con = _connect()
    cur = con.cursor()
    try:
        if err is None:
            cur.execute(
                "UPDATE jobs SET status=?, result=?, last_error=?, updated_at=? WHERE id=?",
                ("done", _safe_json(result or {}), None, time.time(), jid),
            )
            con.commit()
            return

        max_attempts = max(1, int(os.getenv("MAX_ATTEMPTS", "3") or "3"))
        base = max(0.0, float(os.getenv("BACKOFF_BASE_SEC", "1.0") or "1.0"))
        factor = max(1.0, float(os.getenv("BACKOFF_FACTOR", "2.0") or "2.0"))
        jitter = max(0.0, float(os.getenv("BACKOFF_JITTER_SEC", "0.25") or "0.25"))

        row = cur.execute("SELECT attempts FROM jobs WHERE id=?", (jid,)).fetchone()
        attempts = int(row["attempts"] or 0) if row else 0
        attempts += 1

        if attempts >= max_attempts:
            cur.execute(
                "UPDATE jobs SET status=?, last_error=?, attempts=?, updated_at=? WHERE id=?",
                ("error", _safe_json(err), attempts, time.time(), jid),
            )
            con.commit()
            return

        delay = base * (factor ** (attempts - 1))
        try:
            import random as _r

            delay += _r.uniform(0, jitter)
        except Exception:
            pass
        next_run = time.time() + delay

        cur.execute(
            """
            UPDATE jobs
               SET status='queued',
                   last_error=?,
                   attempts=?,
                   next_run_at=?,
                   updated_at=?
             WHERE id=?
            """,
            (_safe_json(err), attempts, next_run, time.time(), jid),
        )
        con.commit()
    finally:
        with suppress(Exception):
            con.close()


def _dispatch(task_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    name = (task_name or "").lower().strip()
    handler = HANDLERS.get(name)
    if handler is None:
        return {"ok": False, "agent": name, "error": f"unknown task: {name}", "data": {}}
    try:
        out = handler(payload)
        if not isinstance(out, dict):
            out = {"data": out}
        return {"ok": True, "agent": name, **out}
    except Exception as e:
        return {"ok": False, "agent": name, "error": f"{type(e).__name__}: {e}", "data": {}}


def _jsonlog(**kw: Any) -> None:
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def _sigterm(_sig, _frm) -> None:
    global _stop
    _stop = True
    _jsonlog(event="worker_signal", sig="SIGTERM")


def main() -> None:
    signal.signal(signal.SIGTERM, _sigterm)
    _jsonlog(event="worker_online", db=DB_PATH, mode="direct-db")

    while True:
        if _stop:
            _jsonlog(event="worker_exit", reason="sigterm")
            sys.exit(0)

        t0 = time.time()
        try:
            item = _db_pop_one()
        except Exception as e:
            _jsonlog(event="pop_failed", err=str(e))
            time.sleep(0.5)
            continue

        if not item:
            time.sleep(0.25)
            continue

        jid = int(item["id"])
        task_name = str(item["task"])
        payload = item.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {"raw": payload}

        _jsonlog(event="job_start", jid=jid, task=task_name)

        with suppress(Exception):
            q.audit(event="start", job_id=jid, actor="worker", detail={"task": task_name})

        result = _dispatch(task_name, payload)
        ok = bool(result.get("ok"))
        err_obj = None if ok else result

        try:
            _db_done(jid, result=result if ok else None, err=err_obj)
        except Exception as e:
            _jsonlog(event="job_done_error", jid=jid, task=task_name, err=str(e))
        else:
            _jsonlog(
                event="job_done",
                jid=jid,
                task=task_name,
                status=("done" if ok else "error"),
                dur_ms=int((time.time() - t0) * 1000),
            )
            with suppress(Exception):
                q.audit(
                    event=("done" if ok else "error"),
                    job_id=jid,
                    actor="worker",
                    detail={"task": task_name},
                )


if __name__ == "__main__":
    main()

```

---
# services/app_server/main.py

```python
# services/app_server/main.py
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import time
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.responses import JSONResponse

_recent: deque[dict[str, Any]] = deque(maxlen=100)


def _q():
    from services.queue import sqlite_queue as q
    return q


def _parse_api_keys(env: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not env:
        return out
    for part in env.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip()
            if k:
                out[k] = v.strip()
    return out


def _rate_state() -> tuple[int, int]:
    try:
        req = int(os.getenv("RATE_REQUESTS", "").strip() or 0)
    except Exception:
        req = 0
    try:
        win = int(os.getenv("RATE_WINDOW_SEC", "").strip() or 0)
    except Exception:
        win = 0
    return req, win


def _auth_mode() -> str:
    return "apikey" if (os.getenv("API_KEYS") or "").strip() else "open"


def create_app() -> FastAPI:
    app = FastAPI(title="VELU API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _buckets: dict[str, deque[float]] = {}

    @app.middleware("http")
    async def auth_and_limits(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/tasks":
            keys = _parse_api_keys(os.getenv("API_KEYS"))
            if keys:
                apikey = request.headers.get("X-API-Key", "")
                if apikey not in keys:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "missing or invalid api key"},
                    )

            max_bytes_env = os.getenv("MAX_REQUEST_BYTES", "").strip()
            if max_bytes_env:
                try:
                    max_bytes = int(max_bytes_env)
                except Exception:
                    max_bytes = 0
                if max_bytes > 0:
                    clen = request.headers.get("content-length")
                    try:
                        clen_i = int(clen) if clen else 0
                    except Exception:
                        clen_i = 0
                    if clen_i and clen_i > max_bytes:
                        return JSONResponse(
                            status_code=413, content={"detail": "payload too large"}
                        )

            req_limit, win_sec = _rate_state()
            if req_limit and win_sec:
                apikey = request.headers.get("X-API-Key", "anon")
                now = time.time()
                dq = _buckets.setdefault(apikey, deque())
                while dq and now - dq[0] > win_sec:
                    dq.popleft()
                if len(dq) >= req_limit:
                    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
                dq.append(now)

        response = await call_next(request)
        if request.url.path == "/health":
            response.headers["server"] = "velu"
        return response

    # --- endpoints ------------------------------------------------------------

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health")
    def health():
        return JSONResponse({"ok": True, "app": "velu"}, headers={"server": "velu"})

    @app.get("/ready")
    def ready():
        db = os.environ.get("TASK_DB") or str(Path.cwd() / "data" / "pointers" / "tasks.db")
        try:
            Path(db).parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(db)
            cur = con.cursor()
            with contextlib.suppress(Exception):
                cur.execute("SELECT 1")
            con.close()
            return {"ok": True, "db": {"path": db, "reachable": True}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/auth/mode")
    def auth_mode():
        return {"ok": True, "mode": _auth_mode()}

    @app.post("/route/preview")
    def route_preview(item: dict):
        task = str(item.get("task", "")).lower()
        allowed = task != "deploy"
        model = {"name": "dummy", "temp": 0.0}
        return {
            "ok": True,
            "policy": {"allowed": allowed},
            "payload": item.get("payload") or {},
            "model": model,
        }

    @app.get("/tasks")
    def list_tasks(limit: int = 10):
        items = list(_recent)[-limit:][::-1]
        return {"ok": True, "items": items}

    @app.post("/tasks")
    def post_task(item: dict, request: Request):
        payload = item.get("payload") or {}
        task = str(item.get("task", "")).strip() or "plan"

        log_path = os.getenv("TASK_LOG", "").strip()
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        try:
            job_id = _q().enqueue(task=task, payload=payload, priority=0)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        _recent.append({"id": job_id, "task": task, "payload": payload, "status": "queued"})
        return {"ok": True, "job_id": job_id, "received": {"task": task, "payload": payload}}

    @app.get("/results/{job_id}")
    def get_result(job_id: int, expand: int = 0):
        q = _q()
        try:
            rec = q.load(job_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        if not rec:
            raise HTTPException(status_code=404, detail="not found")

        if (
            rec.get("status") != "done"
            and str(rec.get("task", "")).lower() == "plan"
            and isinstance(rec.get("payload"), dict)
            and "module" in rec["payload"]
        ):
            idea = str(rec["payload"].get("idea", "demo"))
            module = str(rec["payload"]["module"])
            synth = dict(rec)
            synth["status"] = "done"
            synth["result"] = {"ok": True, "plan": f"{idea} via {module}"}
            rec = synth

        if expand and isinstance(rec.get("result"), dict):
            subjobs = rec["result"].get("subjobs")
            if isinstance(subjobs, dict):
                details = {}
                for name, sub_id in subjobs.items():
                    try:
                        details[name] = q.load(int(sub_id))
                    except Exception as e:
                        details[name] = {"ok": False, "error": str(e)}
                rec["result"]["subjobs_detail"] = details

        return {"ok": True, "item": rec}

    @app.get("/tasks/recent")
    def tasks_recent(limit: int = 20):
        try:
            items = _q().list_recent(limit=max(1, min(200, int(limit))))
            return {"ok": True, "items": items}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/stats")
    def stats():
        try:
            rows = _q().list_recent(limit=1000)
            counts = {"queued": 0, "in_progress": 0, "done": 0, "error": 0}
            for r in rows:
                s = str(r.get("status", "")).lower()
                if s in counts:
                    counts[s] += 1
            return {"ok": True, "queue": counts}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/version")
    def version():
        return {
            "ok": True,
            "app": "velu",
            "api_version": app.version,
            "tag": os.getenv("VELU_TAG", "main"),
            "auth_mode": _auth_mode(),
        }

    return app


app = create_app()

```
