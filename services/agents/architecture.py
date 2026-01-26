from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


Frontend = Literal["nextjs", "react", "vue", "flutter", "tauri", "none"]
Backend = Literal["fastapi", "node", "none"]
Database = Literal["sqlite", "postgres", "none"]
Kind = Literal["website", "web_app", "mobile_app", "dashboard", "api_only"]


class StackSpec(TypedDict):
    frontend: Frontend
    backend: Backend
    database: Database
    kind: Kind
    ui_locales: List[str]


def _norm_str(value: Any, default: str) -> str:
    s = str(value).strip() if value is not None else ""
    return s or default


def _norm_list(values: Any) -> List[str]:
    if isinstance(values, list):
        return [str(v).strip() for v in values if str(v).strip()]
    return []


def _pick_frontend(value: Any) -> Frontend:
    v = _norm_str(value, "nextjs").lower()
    if v in {"react"}:
        return "react"
    if v in {"vue"}:
        return "vue"
    if v in {"flutter"}:
        return "flutter"
    if v in {"tauri"}:
        return "tauri"
    if v in {"none", "api_only"}:
        return "none"
    return "nextjs"


def _pick_backend(value: Any) -> Backend:
    v = _norm_str(value, "fastapi").lower()
    if v in {"node", "express", "nestjs"}:
        return "node"
    if v in {"none", "api_only"}:
        return "none"
    return "fastapi"


def _pick_database(value: Any) -> Database:
    v = _norm_str(value, "sqlite").lower()
    if v in {"postgres", "postgresql"}:
        return "postgres"
    if v in {"none"}:
        return "none"
    return "sqlite"


def _pick_kind(value: Any) -> Kind:
    v = _norm_str(value, "web_app").lower()
    if v in {"website", "landing"}:
        return "website"
    if v in {"mobile_app", "mobile"}:
        return "mobile_app"
    if v in {"dashboard"}:
        return "dashboard"
    if v in {"api_only", "api"}:
        return "api_only"
    return "web_app"


def _extract_locales(payload: Dict[str, Any]) -> List[str]:
    direct = _norm_list(payload.get("locales"))
    if direct:
        return direct

    product = payload.get("product")
    if isinstance(product, dict):
        from_product = _norm_list(product.get("locales"))
        if from_product:
            return from_product

    spec = payload.get("localization")
    if isinstance(spec, dict):
        from_spec = _norm_list(spec.get("supported_languages"))
        if from_spec:
            return from_spec

    return ["en"]


def _pick_blueprint_id(idea: str, stack: StackSpec, payload: Dict[str, Any]) -> Optional[str]:
    """
    Decide which blueprint to use, if any.

    Rule: if request looks like a "shop" and stack is fastapi + nextjs + sqlite,
    return blueprint id "shop_fastapi_next".
    """
    text = " ".join(
        [
            idea or "",
            str(payload.get("module") or ""),
            str(payload.get("kind") or ""),
            str(payload.get("product") or ""),
        ]
    ).lower()

    shop_keywords = {
        "shop",
        "store",
        "ecommerce",
        "e-commerce",
        "catalog",
        "product",
        "products",
        "cart",
        "checkout",
        "order",
        "orders",
        "admin",
        "rbac",
        "login",
        "jwt",
    }

    looks_like_shop = any(k in text for k in shop_keywords)

    is_shop_stack = (
        stack["backend"] == "fastapi"
        and stack["frontend"] == "nextjs"
        and stack["database"] == "sqlite"
        and stack["kind"] in ("web_app", "dashboard")
    )

    if looks_like_shop and is_shop_stack:
        return "shop_fastapi_next"

    return None


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    idea = _norm_str(payload.get("idea"), "demo")
    module = _norm_str(payload.get("module"), "hello_mod")

    stack: StackSpec = {
        "frontend": _pick_frontend(payload.get("frontend")),
        "backend": _pick_backend(payload.get("backend")),
        "database": _pick_database(payload.get("database")),
        "kind": _pick_kind(payload.get("kind")),
        "ui_locales": _extract_locales(payload),
    }

    blueprint_id = _pick_blueprint_id(idea=idea, stack=stack, payload=payload)

    return {
        "ok": True,
        "agent": "architecture",
        "idea": idea,
        "module": module,
        "stack": stack,
        "blueprint_id": blueprint_id,
    }
