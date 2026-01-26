# services/app_server/main.py
from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import time
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
from typing import Callable
from services.app_server.task_policy import allowed_tasks_for_claims

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from services.app_server.routes import tasks_allowed
from services.app_server import admin as admin_routes
from services.app_server import store_sqlite
from services.app_server.auth import ApiKeyRequiredMiddleware, claims_from_request, key_id, using_postgres_api_keys
from services.app_server.dependencies.scopes import require_scopes
from services.app_server.routes import jobs as jobs_routes
from services.app_server.routes import orgs
from services.app_server.routes import blueprints, i18n, assistant
from services.app_server.security.headers import SecurityHeadersMiddleware
from services.contracts.jobs import JobCreate, job_item_from_row, sanitize_json
from services.db.migrate import migrate
from services.queue.jobs import enqueue_job, get_job, list_recent_for_org, using_postgres
from services.queue.jobs import list_recent as jobs_list_recent


from services.queue.worker_entry import HANDLERS as WORKER_HANDLERS

logger = logging.getLogger(__name__)

_recent: deque[dict[str, Any]] = deque(maxlen=100)
ALLOWED_TASKS: set[str] = set(WORKER_HANDLERS.keys())

ENV = os.getenv("ENV", "local").lower()

SECRET_KEY = os.getenv("SECRET_KEY") or ""
JWT_SECRET = os.getenv("JWT_SECRET") or SECRET_KEY

ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in ALLOWED_ORIGINS_RAW.split(",") if o.strip()]


def _require_secret(name: str, value: str | None) -> None:
    if ENV in {"local", "test"}:
        return
    if not value:
        raise RuntimeError(f"{name} must be set when ENV={ENV}. Set it as an environment variable before starting the API.")


class TaskIn(BaseModel):
    task: str = Field(min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


def _q():
    from services.queue import sqlite_queue as q

    return q


def _truthy_env(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


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


def get_auth_mode() -> str:
    mode = (os.getenv("AUTH_MODE") or "").strip().lower()
    if mode in {"apikey", "jwt"}:
        return mode
    if os.getenv("API_KEYS"):
        return "apikey"
    if os.getenv("AUTH_JWT_SECRET") or os.getenv("AUTH_JWT_PUBLIC_KEY"):
        return "jwt"
    return "apikey"


def _cors_origins() -> list[str]:
    cors_env = (os.getenv("CORS_ORIGINS") or "").strip()
    if cors_env:
        return [o.strip() for o in cors_env.split(",") if o.strip()]
    if ENV in {"local", "test"}:
        return ["*"]
    return ALLOWED_ORIGINS


def client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _tier_rank(tier: str) -> int:
    t = (tier or "").strip().lower()
    if t in {"premium", "superhero"}:
        return 30
    if t in {"standard", "hero"}:
        return 20
    if t in {"basic", "base"}:
        return 10
    return 0



def _role_rank(role: str) -> int:
    r = (role or "").strip().lower()
    if r == "viewer":
        return 10
    if r == "builder":
        return 20
    return 30


def require_role(min_role: str):
    enforce = (os.getenv("ENFORCE_ROLES") or "").strip().lower() in {"1", "true", "yes"}

    async def _dep(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> str:
        if not enforce:
            return "admin"
        if not (os.getenv("API_KEYS") or "").strip() and not using_postgres():
            return "admin"
        c = claims_from_request(request)
        if not c:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid API key")
        role = c.get("role", "admin")
        if _role_rank(role) < _role_rank(min_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return role

    return _dep


def require_tier(min_tier: str):
    enforce = (os.getenv("ENFORCE_TIERS") or "").strip().lower() in {"1", "true", "yes"}

    async def _dep(request: Request) -> str:
        if not enforce:
            return "base"
        if not (os.getenv("API_KEYS") or "").strip() and not using_postgres():
            return "superhero"
        c = claims_from_request(request)
        if not c:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid api key")
        tier = c.get("tier", "superhero")
        if _tier_rank(tier) < _tier_rank(min_tier):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="upgrade required")
        return tier

    return _dep


TASK_POLICY_MIN_ROLE: dict[str, str] = {
    "plan": "viewer",
    "chat": "viewer",
    "ui_scaffold": "builder",
    "packager": "builder",
    "deploy": "admin",
}
DEFAULT_TASK_MIN_ROLE = "builder"


def create_app() -> FastAPI:
    if os.getenv("VELU_TESTING") != "1":
        _require_secret("SECRET_KEY", SECRET_KEY)
        _require_secret("JWT_SECRET", JWT_SECRET)

    if os.getenv("VELU_RUN_MIGRATIONS", "1") == "1":
        migrate()

    app = FastAPI(title="VELU API", version="1.0.0")

    origins = _cors_origins()
    allow_all = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False if allow_all else True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.include_router(
        admin_routes.router,
        prefix="/admin",
        dependencies=[Depends(require_scopes({"admin:api_keys:manage"}))],
    )
    app.include_router(jobs_routes.router)
    app.include_router(orgs.router)
    app.include_router(tasks_allowed.router)

    app.add_middleware(SecurityHeadersMiddleware)

    keys_env = (os.getenv("API_KEYS") or "").strip()
    admin_env = (os.getenv("VELU_ADMIN_KEY") or "").strip() or (os.getenv("TEST_PLATFORM_ADMIN_KEY") or "").strip()

    enable_auth = using_postgres_api_keys() or bool(keys_env)
    if ENV not in {"test", "local"} and admin_env:
        enable_auth = True
    if enable_auth:
        app.add_middleware(ApiKeyRequiredMiddleware)

    _buckets_key: dict[str, deque[float]] = {}
    _buckets_ip: dict[str, deque[float]] = {}

    app.include_router(blueprints.router, dependencies=[Depends(require_role("builder"))])
    app.include_router(i18n.router, dependencies=[Depends(require_role("viewer"))])
    app.include_router(assistant.router, dependencies=[Depends(require_role("viewer"))])

    def _audit_write(rec: dict[str, Any]) -> None:
        path = (os.getenv("AUDIT_LOG") or "").strip()
        if not path:
            return
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("AUDIT_LOG write failed")

    @app.middleware("http")
    async def size_rate_and_audit(request: Request, call_next):
        started = time.time()

        # ✅ Parse once, store once (so dependencies see it)
        c = getattr(request.state, "claims", None)
        if not c:
            c = claims_from_request(request) or {}
            request.state.claims = c

        if request.method == "POST" and request.url.path in {"/tasks", "/assistant-chat"}:
            max_bytes_env = (os.getenv("MAX_REQUEST_BYTES") or "").strip()
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
                        return JSONResponse(status_code=413, content={"detail": "payload too large"})

        req_limit, win_sec = _rate_state()
        if req_limit and win_sec:
            now = time.time()

            token = (c or {}).get("_token", "")
            if token:
                bucket_key = key_id(token)
            else:
                if _truthy_env("RATE_LIMIT_BY_IP"):
                    bucket_key = f"ip:{client_ip(request)}"
                else:
                    bucket_key = "anon"

            dqk = _buckets_key.setdefault(bucket_key, deque())
            while dqk and now - dqk[0] > win_sec:
                dqk.popleft()
            if len(dqk) >= req_limit:
                return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
            dqk.append(now)

            if _truthy_env("RATE_LIMIT_BY_IP") and not str(bucket_key).startswith("ip:"):
                ip = client_ip(request)
                dqi = _buckets_ip.setdefault(ip, deque())
                while dqi and now - dqi[0] > win_sec:
                    dqi.popleft()
                if len(dqi) >= req_limit:
                    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
                dqi.append(now)

        response = await call_next(request)

        try:
            # ✅ Reuse the same claims (don’t parse again)
            rec = {
                "ts": int(time.time()),
                "ms": int((time.time() - started) * 1000),
                "method": request.method,
                "path": request.url.path,
                "status": getattr(response, "status_code", None),
                "kid": c.get("kid") or getattr(request.state, "kid", "anon"),
                "role": c.get("role", ""),
                "tier": c.get("tier", ""),
                "org_id": c.get("org_id"),
                "ip": client_ip(request) if _truthy_env("AUDIT_LOG_INCLUDE_IP") else None,
            }
            _audit_write(rec)
        except Exception:
            logger.exception("audit log failure")

        if request.url.path == "/health":
            response.headers["server"] = "velu"
        return response

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
        return {"ok": True, "mode": get_auth_mode()}

    @app.post("/route/preview", dependencies=[Depends(require_role("viewer"))])
    def route_preview(item: dict):
        task = str(item.get("task", "")).lower()
        allowed = task != "deploy"
        model = {"name": "dummy", "temp": 0.0}
        return {"ok": True, "policy": {"allowed": allowed}, "payload": item.get("payload") or {}, "model": model}

    @app.get("/tasks")
    def list_tasks(limit: int = 10):
        items = list(_recent)[-limit:][::-1]
        return {"ok": True, "items": items}

    @app.post("/tasks", dependencies=[Depends(require_scopes({"jobs:submit"}))])
    def post_task(body: TaskIn, request: Request):
        c = getattr(request.state, "claims", None) or claims_from_request(request) or {}
        org_id = c.get("org_id")
        project_id = c.get("project_id")


        enforce = _truthy_env("ENFORCE_ROLES")
        if enforce:
            role = c.get("role", "viewer")
            min_role = TASK_POLICY_MIN_ROLE.get(body.task, DEFAULT_TASK_MIN_ROLE)
            if _role_rank(role) < _role_rank(min_role):
                raise HTTPException(status_code=403, detail="Forbidden")

        task_name = (body.task or "").strip()
        if task_name not in ALLOWED_TASKS:
            raise HTTPException(status_code=400, detail="task_not_allowed")

        enforce_tiers = _truthy_env("ENFORCE_TIERS") or _truthy_env("VELU_ENFORCE_TIERS")
        if ENV in {"local", "test"} and not enforce_tiers:
            pass
        else:
            tier_allowed = allowed_tasks_for_claims(c)
            if task_name not in tier_allowed:
                raise HTTPException(status_code=403, detail="upgrade_required")

        payload = body.payload if isinstance(body.payload, dict) else {}
        payload = dict(payload)

        bad = [k for k in payload.keys() if isinstance(k, str) and k.startswith("_")]
        if bad:
            raise HTTPException(status_code=400, detail="payload_reserved_keys")

        import secrets

        velu_meta: dict[str, Any] = {
            "run_id": secrets.token_hex(8),
            "actor_type": str(c.get("actor_type") or "api_key"),
        }
        aid = c.get("actor_id")
        if aid is not None:
            velu_meta["actor_id"] = str(aid)
        if org_id is not None:
            velu_meta["org_id"] = str(org_id)
        if project_id is not None:
            velu_meta["project_id"] = str(project_id)

        payload["_velu"] = velu_meta

        if using_postgres_api_keys() and org_id:
            payload["_org_id"] = str(org_id)


        client_payload = body.payload if isinstance(body.payload, dict) else {}
        client_payload = dict(client_payload)

        job_in = JobCreate(task=task_name, payload=payload)

        task_obj_queue = {"task": job_in.task, "payload": payload}
        task_obj_client = {"task": job_in.task, "payload": client_payload}



        raw_key = (request.headers.get("X-API-Key") or "").strip()

        job_id = enqueue_job(
        task_obj_queue,
        key=raw_key,
        org_id=org_id,
        project_id=project_id,
        actor_type=c.get("actor_type", "api_key"),
        actor_id=c.get("actor_id"),
        
      )


        backend = (os.environ.get("TASK_BACKEND") or "").lower()
        if backend == "sqlite":
            store_sqlite.insert(task_obj_client)

        task_log = (os.getenv("TASK_LOG") or "").strip()
        if task_log:
            try:
                log_path = Path(task_log)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as f:
                    client_payload = body.payload if isinstance(body.payload, dict) else {}
                    rec = {"task": job_in.task, "payload": sanitize_json(client_payload)}

                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning("Failed to write TASK_LOG: %s", e)

        _recent.append({"id": job_id, "task": job_in.task, "payload": client_payload, "status": "queued"})

        return {"ok": True, "job_id": str(job_id)}



    @app.get(
        "/results/{job_id}",
        dependencies=[Depends(require_role("viewer")), Depends(require_scopes({"jobs:read"}))],
    )
    async def get_result(job_id: str, request: Request, expand: int = 0):
        row = get_job(job_id)
        if not row:
            return {"ok": False, "error": "not_found"}

        item = job_item_from_row(row)
        if isinstance(item, dict) and "id" in item and item["id"] is not None:
            item["id"] = str(item["id"])

        if using_postgres_api_keys():
            claims = getattr(request.state, "claims", None) or claims_from_request(request) or {}

            req_org = claims.get("org_id")


            job_org = item.get("org_id") if isinstance(item, dict) else None
            if not job_org:
                payload = item.get("payload") if isinstance(item, dict) else None
                if isinstance(payload, dict):
                    job_org = payload.get("_org_id")

            if not req_org or str(job_org or "") != str(req_org):
                return {"ok": False, "error": "not_found"}

        return {"ok": True, "item": item}






    @app.get("/tasks/recent")
    def tasks_recent(limit: int = 20):
        lim = max(1, min(200, int(limit)))
        if using_postgres():
            rows = list_recent_for_org(org_id=str("local"), limit=lim)
        else:
            rows = jobs_list_recent(limit=lim)

        items: list[dict[str, Any]] = []
        for row in rows:
            item = job_item_from_row(row)
            if "created_at" not in item:
                item["created_at"] = row.get("created_at") or row.get("ts")
            items.append(item)
        return {"ok": True, "items": items}

    @app.get("/version")
    def version():
        return {"ok": True, "app": "velu", "api_version": app.version, "tag": os.getenv("VELU_TAG", "local"), "auth_mode": get_auth_mode()}

    @app.get("/artifacts/{name}")
    def get_artifact(name: str):
        base = Path.cwd() / "artifacts"
        file_path = base / name
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="artifact not found")
        return FileResponse(file_path, filename=name)

    return app


class _LazyASGIApp:
    def __init__(self, factory: Callable[[], FastAPI]):
        self._factory = factory
        self._app: FastAPI | None = None

    def _get(self) -> FastAPI:
        if self._app is None:
            self._app = self._factory()
        return self._app

    async def __call__(self, scope, receive, send):
        return await self._get()(scope, receive, send)

    def __getattr__(self, name: str):
        return getattr(self._get(), name)


@lru_cache(maxsize=1)
def get_app() -> FastAPI:
    return create_app()


app = _LazyASGIApp(get_app)
