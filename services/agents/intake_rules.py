# services/agents/intake_rules.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

_ALLOWED_TYPES = {
    "website",
    "saas",
    "mobile_app",
    "ecommerce",
    "marketplace",
    "portal",
    "docs",
}

_ALLOWED_GOALS = {
    "lead_gen",
    "self_service",
    "transactions",
    "community",
    "internal_tool",
}


def infer_type_and_goal(idea: str) -> Tuple[str, str]:
    """
    Map the free-text idea to Product.type + Product.goal enums.
    """
    text = (idea or "").lower()

    # --- TYPE ---
    if any(
        w in text
        for w in ("shop", "store", "ecommerce", "e-commerce", "cart", "checkout", "catalog")
    ):
        p_type = "ecommerce"
    elif "marketplace" in text:
        p_type = "marketplace"
    elif "mobile app" in text or ("mobile" in text and "app" in text):
        p_type = "mobile_app"
    elif "portal" in text:
        p_type = "portal"
    elif any(w in text for w in ("docs", "documentation", "knowledge base")):
        p_type = "docs"
    elif any(
        w in text for w in ("dashboard", "saas", "b2b saas", "b2b", "multi-tenant", "multi tenant")
    ):
        p_type = "saas"
    else:
        p_type = "saas"

    # --- GOAL ---
    if any(w in text for w in ("lead", "leads", "landing page", "leadgen", "marketing site")):
        goal = "lead_gen"
    elif any(
        w in text
        for w in (
            "checkout",
            "order",
            "orders",
            "payments",
            "subscription",
            "billing",
            "transactions",
        )
    ):
        goal = "transactions"
    elif any(w in text for w in ("community", "forum", "social")):
        goal = "community"
    elif any(
        w in text for w in ("self-service", "self service", "customer portal", "public portal")
    ):
        goal = "self_service"
    else:
        goal = "internal_tool"

    return p_type, goal


def infer_channels(idea: str, fallback: List[str] | None = None) -> List[str]:
    """
    Map free-text to channels: 'web', 'ios', 'android'.
    """
    text = (idea or "").lower()
    channels: List[str] = list(fallback or [])

    if not channels:
        channels.append("web")

    if any(w in text for w in ("mobile", "react native", "ios", "iphone", "android")):
        if "ios" not in channels:
            channels.append("ios")
        if "android" not in channels:
            channels.append("android")

    # Normalize / deduplicate / filter invalid
    out: List[str] = []
    for ch in channels:
        ch_norm = str(ch).strip().lower()
        if ch_norm in {"web", "ios", "android"} and ch_norm not in out:
            out.append(ch_norm)
    if not out:
        out.append("web")
    return out


def infer_plugins(idea: str) -> List[str]:
    text = (idea or "").lower()
    plugins: List[str] = []

    if any(
        w in text
        for w in (
            "shop",
            "store",
            "ecommerce",
            "e-commerce",
            "cart",
            "checkout",
            "catalog",
            "products",
        )
    ):
        plugins.append("ecommerce")

    if any(
        w in text
        for w in (
            "login",
            "sign in",
            "signup",
            "sign up",
            "auth",
            "authentication",
            "sso",
            "okta",
            "azure ad",
            "oauth",
        )
    ):
        plugins.append("auth")

    if any(
        w in text
        for w in (
            "subscription",
            "subscriptions",
            "billing",
            "stripe",
            "plans",
            "starter plan",
            "pro plan",
            "enterprise plan",
        )
    ):
        if "subscriptions" not in plugins:
            plugins.append("subscriptions")
        if "billing" not in plugins:
            plugins.append("billing")

    # dedupe + sort for stable output
    return sorted(set(plugins))


def infer_database_engine(idea: str, default: str = "sqlite") -> str:
    text = (idea or "").lower()
    if "postgresql" in text or "postgres" in text:
        return "postgres"
    if "mysql" in text or "mariadb" in text:
        return "mysql"
    if "mongodb" in text or "mongo" in text:
        return "mongodb"
    return default


def infer_plan_tier(idea: str, default: str = "starter") -> str:
    text = (idea or "").lower()
    if any(
        w in text
        for w in (
            "multi-tenant",
            "multi tenant",
            "b2b saas",
            "enterprise",
            "sso",
            "okta",
            "azure ad",
            "audit",
            "ip allowlist",
        )
    ):
        return "enterprise"
    if any(w in text for w in ("pro plan", "growth", "scale", "scalable", "uploads", "dashboards")):
        return "pro"
    return default


def enrich_blueprint_dict(blueprint: Dict[str, Any], idea: str) -> Dict[str, Any]:
    """
    Take blueprint.model_dump() dict and tweak backend/db/plugins/plan_tier
    based on the idea text. Works only on the dict level (no Pydantic types).
    """
    text = (idea or "").lower()
    bp = dict(blueprint or {})

    backend = dict(bp.get("backend") or {})
    database = dict(bp.get("database") or {})
    plugins: List[str] = list(bp.get("plugins") or [])
    plan_tier = str(bp.get("plan_tier") or "").strip().lower() or "starter"

    # Backend framework hints from idea
    if "fastapi" in text and not backend.get("framework"):
        backend["framework"] = "fastapi"
    if any(w in text for w in ("node", "express", "nestjs")) and backend.get("framework") is None:
        backend["framework"] = "node"

    # Database
    db_engine_default = str(database.get("engine") or "sqlite")
    database["engine"] = infer_database_engine(idea, default=db_engine_default)

    # Plugins
    inferred = infer_plugins(idea)
    for p in inferred:
        if p not in plugins:
            plugins.append(p)

    # Plan tier
    plan_tier = infer_plan_tier(idea, default=plan_tier)

    bp["backend"] = backend
    bp["database"] = database
    bp["plugins"] = plugins
    bp["plan_tier"] = plan_tier

    return bp
