# services/agents/backend_scaffold.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Set

from services.plugins import PLUGINS  # noqa: F401

logger = logging.getLogger(__name__)
_TPL = Path("templates")  # noqa: F841

# Write backend into generated/services/api so packager includes it.
API_BASE = "generated/services/api"
API_BASE_COMPAT = "services/api"

def _read(p: Path, default: str = "") -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception as exc:  # nosec B110
        logger.debug("Failed to read %s: %s", p, exc)
        return default

RUN_API_SH = """#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export PYTHONPATH="."
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8000}"

exec python -m uvicorn generated.services.api.app:app --reload --host "$HOST" --port "$PORT"
"""

def _fastapi_app_py(has_auth: bool, has_ecommerce: bool) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "from fastapi import FastAPI",
        "",
        "",
        "def create_app() -> FastAPI:",
        "    app = FastAPI(title='App', version='1.0.0')",
        "    from .routes import health",
        "    app.include_router(health.router)",
    ]
    if has_auth:
        lines += [
            "    from .routes import auth",
            "    app.include_router(auth.router)",
        ]
    if has_ecommerce:
        lines += [
            "    from .routes import products",
            "    app.include_router(products.router)",
        ]
    lines += [
        "    return app",
        "",
        "",
        "app = create_app()",
        "",
    ]
    return "\n".join(lines)

HEALTH_ROUTE = """from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"ok": True}
"""

AUTH_ROUTE_FASTAPI = """
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

_FAKE_USERS: Dict[str, str] = {}

@router.post("/register")
async def register(req: RegisterRequest):
    if req.email in _FAKE_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )
    _FAKE_USERS[req.email] = req.password
    return {"ok": True, "email": req.email}

@router.post("/login")
async def login(req: LoginRequest):
    stored = _FAKE_USERS.get(req.email)
    if stored is None or stored != req.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = "demo-token"
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": req.email,
    }

@router.get("/me")
async def me():
    return {"email": "demo@example.com"}
""".lstrip()

PRODUCTS_ROUTE_FASTAPI = """
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/products", tags=["products"])

_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Classic T-Shirt",
        "price": 19.99,
        "currency": "EUR",
        "in_stock": True,
        "image_url": "https://placehold.co/400x400?text=T-Shirt",
        "description": "Soft cotton tee with your brand logo.",
    },
    {
        "id": 2,
        "name": "Premium Hoodie",
        "price": 49.99,
        "currency": "EUR",
        "in_stock": True,
        "image_url": "https://placehold.co/400x400?text=Hoodie",
        "description": "Warm hoodie for colder days.",
    },
    {
        "id": 3,
        "name": "Sneakers",
        "price": 79.0,
        "currency": "EUR",
        "in_stock": False,
        "image_url": "https://placehold.co/400x400?text=Sneakers",
        "description": "Comfortable sneakers, currently out of stock.",
    },
]

@router.get("")
async def list_products():
    return _PRODUCTS

@router.get("/{product_id}")
async def get_product(product_id: int):
    for p in _PRODUCTS:
        if p.get("id") == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")
""".lstrip()

def _node_express_files() -> list[dict[str, str]]:
    app_js = (
        'import express from "express";\n\n'
        "const app = express();\n"
        "app.use(express.json());\n\n"
        'app.get("/health", (_req, res) => {\n'
        "  res.json({ ok: true });\n"
        "});\n\n"
        "const port = process.env.PORT || 8000;\n"
        "app.listen(port, () => {\n"
        "  console.log(`API listening on ${port}`);\n"
        "});\n"
    )
    package_json = (
        "{\n"
        '  "name": "velu-node-api",\n'
        '  "private": true,\n'
        '  "type": "module",\n'
        '  "scripts": {\n'
        '    "dev": "node app.js"\n'
        "  },\n"
        '  "dependencies": {\n'
        '    "express": "^4.21.0"\n'
        "  }\n"
        "}\n"
    )
    return [
        {"path": "generated/services/node/app.js", "content": app_js},
        {"path": "generated/services/node/package.json", "content": package_json},
    ]

def _resolve_backend(payload: dict[str, Any]) -> str:
    bp = payload.get("blueprint")
    if isinstance(bp, dict):
        b_stack = bp.get("backend") or {}
        if isinstance(b_stack, dict):
            fw = b_stack.get("framework")
            if isinstance(fw, str) and fw.strip():
                return fw.strip().lower()
    raw = payload.get("backend") or "fastapi"
    return str(raw).strip().lower() or "fastapi"

def _extract_plugins(payload: dict[str, Any]) -> Set[str]:
    raw = payload.get("plugins") or []
    plugins: Set[str] = set()
    if isinstance(raw, (list, tuple, set)):
        for p in raw:
            text = str(p or "").strip().lower()
            if text:
                plugins.add(text)
    return plugins

def handle(payload: dict[str, Any]) -> dict[str, Any]:
    backend = _resolve_backend(payload)
    plugins = _extract_plugins(payload)

    plugin_backend_tags: Set[str] = set()
    for slug in plugins:
        plugin = PLUGINS.get(slug)
        if plugin:
            plugin_backend_tags.update(plugin.backend_tags)

    if backend in ("node", "express", "nestjs"):
        files = _node_express_files()
        return {
            "ok": True,
            "agent": "backend_scaffold",
            "backend": "node",
            "files": files,
            "plugin_backend_tags": sorted(plugin_backend_tags),
        }

    # default: fastapi
    has_auth = "auth" in plugins
    has_ecommerce = "ecommerce" in plugins

    files: list[dict[str, str]] = []

    app_py = _fastapi_app_py(has_auth, has_ecommerce)

    # --- canonical (packager-friendly) ---
    files.append({"path": f"{API_BASE}/__init__.py", "content": ""})
    files.append({"path": f"{API_BASE}/routes/__init__.py", "content": ""})
    files.append({"path": f"{API_BASE}/app.py", "content": app_py})
    files.append({"path": f"{API_BASE}/routes/health.py", "content": HEALTH_ROUTE})

    # --- compat (older tests expect repo-root services/api) ---
    files.append({"path": f"{API_BASE_COMPAT}/__init__.py", "content": ""})
    files.append({"path": f"{API_BASE_COMPAT}/routes/__init__.py", "content": ""})
    files.append({"path": f"{API_BASE_COMPAT}/app.py", "content": app_py})
    files.append({"path": f"{API_BASE_COMPAT}/routes/health.py", "content": HEALTH_ROUTE})

    files.append({"path": "run_api.sh", "content": RUN_API_SH})

    if has_auth:
        files.append({"path": f"{API_BASE}/routes/auth.py", "content": AUTH_ROUTE_FASTAPI})
        files.append({"path": f"{API_BASE_COMPAT}/routes/auth.py", "content": AUTH_ROUTE_FASTAPI})

    if has_ecommerce:
        files.append({"path": f"{API_BASE}/routes/products.py", "content": PRODUCTS_ROUTE_FASTAPI})
        files.append({"path": f"{API_BASE_COMPAT}/routes/products.py", "content": PRODUCTS_ROUTE_FASTAPI})


    return {
        "ok": True,
        "agent": "backend_scaffold",
        "backend": "fastapi",
        "files": files,
        "plugin_backend_tags": sorted(plugin_backend_tags),
    }
