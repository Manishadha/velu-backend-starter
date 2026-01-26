from __future__ import annotations

import os
from typing import Any, Dict, List, Set  # noqa: F401

from services.queue.worker_entry import HANDLERS as WORKER_HANDLERS


def env() -> str:
    return (os.getenv("ENV") or "local").strip().lower()


def plan_slug() -> str:
    return (os.getenv("VELU_PLAN") or "base").strip().lower()


def plan_label(slug: str) -> str:
    m = {
        "base": "Base — basic tasks",
        "hero": "Hero — advanced tasks",
        "superhero": "Superhero — all tasks",
    }
    return m.get(slug, f"{slug} — tasks")


def tier_slug_from_plan(plan: str) -> str:
    m = {
        "base": "starter",
        "hero": "growth",
        "superhero": "enterprise",
    }
    return m.get((plan or "").strip().lower(), "starter")


def tier_label(slug: str) -> str:
    m = {
        "starter": "Starter — essentials",
        "growth": "Growth — advanced build",
        "enterprise": "Enterprise — full suite",
    }
    return m.get(slug, slug)

def _normalize_tier_slug(tier: str) -> str:
    t = (tier or "").strip().lower()
    # accept both old + new names
    if t in {"starter", "basic", "base"}:
        return "starter"
    if t in {"growth", "standard", "hero"}:
        return "growth"
    if t in {"enterprise", "premium", "superhero"}:
        return "enterprise"
    return ""


def _allowed_tasks_for_tier_slug(tier_slug: str) -> Set[str]:
    starter = {
        "assistant_intake",
        "blueprint_from_intake",
    }

    growth = starter | {
        "plan",
        "requirements",
        "architecture",
        "datamodel",
        "api_design",
        "ui_scaffold",
        "backend_scaffold",
        "ai_features",
        "security_hardening",
        "testgen",
        "aggregate",
        "report",
        "pipeline",
        "pipeline_waiter",
    }

    if tier_slug == "enterprise":
        wanted = set(WORKER_HANDLERS.keys())
    elif tier_slug == "growth":
        wanted = growth
    else:
        wanted = starter

    existing = set(WORKER_HANDLERS.keys())
    return wanted & existing


def allowed_tasks_for_claims(claims: Dict[str, Any] | None) -> Set[str]:
    c = claims or {}
    tier_raw = (c.get("tier") or "").strip().lower()
    tier = _normalize_tier_slug(tier_raw)

    if not tier:
        # derive from server plan if no tier in claims
        tier = tier_slug_from_plan(plan_slug())

    return _allowed_tasks_for_tier_slug(tier)



def tasks_allowed_response(claims: Dict[str, Any] | None = None) -> Dict[str, Any]:
    plan = plan_slug()
    tier_raw = (claims or {}).get("tier") or tier_slug_from_plan(plan)
    tier = _normalize_tier_slug(str(tier_raw)) or tier_slug_from_plan(plan)

    allowed = sorted(list(_allowed_tasks_for_tier_slug(tier)))

    return {
        "ok": True,
        "env": env(),
        "plan": plan,
        "plan_info": {
            "slug": plan,
            "name": plan.capitalize(),
            "label": plan_label(plan),
        },
        "tier": tier,
        "tier_info": {
            "slug": tier,
            "name": tier.replace("_", " ").title(),
            "label": tier_label(tier),
        },
        "allowed": allowed,
    }


