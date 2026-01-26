# services/agents/chat.py
from __future__ import annotations

from asyncio.log import logger
import os
import json
import queue  # noqa: F401
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple
from services.queue import jobs_sqlite
from services.agents import repo_summary as repo_summary_agent  # noqa: F401


from services.llm import client as llm_client  # noqa: F401
from services.llm.client import RemoteLLMError, remote_chat_completion  # noqa: F401
import logging

logger = logging.getLogger(__name__)  # noqa: F811
from services.queue import get_queue  # noqa: E402

q = get_queue()


MAX_HISTORY = 40
HISTORY_TAIL = 10

BACKENDS = {"rules", "local_llm", "remote_llm"}
DEFAULT_BACKEND = os.getenv("VELU_CHAT_BACKEND", "rules").lower()
OPENAI_MODEL = os.getenv("VELU_OPENAI_MODEL", "gpt-4.1-mini")

REQUIRED_FIELDS = [
    "product_type",
    "goal",
    "main_features",
    "pages",
    "target_users",
    "platform",
    "frontend",
    "backend",
    "database",
    "design_style",
    "module_name",
]


def _extract_stack_info_from_result(
    result: Dict[str, Any],
) -> Tuple[str | None, str | None, str | None]:
    """
    Try to pull kind / backend / database from a pipeline / intake result.

    Returns: (kind, backend_framework, db_engine)
    Each value may be None – packager.handle is fine with that.
    """
    if not result:
        return None, None, None

    # try several common shapes
    blueprint = (
        result.get("blueprint")
        or result.get("spec", {}).get("blueprint")
        or result.get("spec")
        or {}
    )

    kind = blueprint.get("kind") or blueprint.get("type") or None

    backend = None
    backend_info = blueprint.get("backend") or {}
    if isinstance(backend_info, dict):
        backend = (
            backend_info.get("framework")
            or backend_info.get("engine")
            or backend_info.get("type")
            or None
        )

    database = None
    db_info = blueprint.get("database") or {}
    if isinstance(db_info, dict):
        database = db_info.get("engine") or db_info.get("type") or db_info.get("driver") or None

    return kind, backend, database


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _compute_repo_summary_for_spec(spec: Dict[str, Any]) -> Dict[str, Any] | None:
    if not spec.get("use_repo_summary"):
        return None

    root = spec.get("repo_root") or "."
    focus = spec.get("repo_focus_dirs")

    payload = {
        "root": root,
        "focus_dirs": focus,
        "include_snippets": False,  # safe default
    }

    try:
        out = repo_summary_agent.handle(payload)
        if not isinstance(out, dict) or not out.get("ok"):
            return None

        # Keep it small + stable for UI + planning
        stats = out.get("stats") or {}
        languages = out.get("languages") or {}
        return {
            "ok": True,
            "root": str(root),
            "stats": {
                "total_files_seen": stats.get("total_files_seen", 0),
                "top_dirs": stats.get("top_dirs", {}),
                "by_ext": stats.get("by_ext", {}),
                "focus_dirs": stats.get("focus_dirs", {}),
            },
            "languages": languages,
        }
    except Exception:
        return None


def _queue_db_path() -> Path:
    env = os.getenv("TASK_DB")
    if env:
        return Path(env)
    return _repo_root() / "data" / "jobs.db"


def _get_job_full(job_id: int | None) -> Dict[str, Any] | None:
    if not job_id:
        return None
    db_path = _queue_db_path()
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        with conn:
            row = conn.execute(
                "SELECT id, status, result, err FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            logger.debug("chat: failed to close SQLite connection cleanly", exc_info=True)
    if not row:
        return None
    out = dict(row)
    # decode JSON result/err if present
    for k in ("result", "err"):
        v = out.get(k)
        if isinstance(v, str) and v.strip():
            try:
                out[k] = json.loads(v)
            except Exception:
                out[k] = v
    return out


def _format_repo_summary_for_assistant(result_obj: Dict[str, Any]) -> str:
    stats = (result_obj or {}).get("stats") or {}
    langs = (result_obj or {}).get("languages") or {}
    total = stats.get("total_files_seen", 0)
    top_dirs = stats.get("top_dirs") or {}
    top3_dirs = sorted(top_dirs.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:3]

    lines = [
        "Repo summary (safe scan):",
        f"- Total files: {total}",
    ]
    if top3_dirs:
        lines.append("- Top dirs: " + ", ".join([f"{d}({c})" for d, c in top3_dirs]))
    if top3_langs:
        lines.append(
            "- Languages: " + ", ".join([f"{l}({c})" for l, c in top3_langs])  # noqa: E741
        )  # noqa: E741
    return "\n".join(lines)


def _get_job(job_id: int | None) -> Dict[str, Any] | None:
    if not job_id:
        return None

    db_path = _queue_db_path()
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        with conn:
            row = conn.execute(
                "SELECT id, task, result FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            logger.debug(
                "chat: failed to close SQLite connection cleanly",
                exc_info=True,
            )
            pass

    if not row:
        return None
    return dict(row)


def _job_result_json(job: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not job:
        return None
    raw = job.get("result")
    if not raw:
        return None
    if isinstance(raw, (dict, list)):
        return raw if isinstance(raw, dict) else {"_": raw}
    try:
        return json.loads(raw)
    except Exception:
        return None


def _session_dir() -> Path:
    d = _repo_root() / "data" / "chat_sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _trim_history(session: dict) -> None:
    hist = session.get("history") or []
    if len(hist) > MAX_HISTORY:
        session["history"] = hist[-MAX_HISTORY:]


def _session_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")) or "default"
    return _session_dir() / f"{safe}.json"


def _new_session(session_id: str) -> Dict[str, Any]:
    now = time.time()
    return {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "stage": "collecting",
        "spec": {},
        "history": [],
        "jobs": {},
        "backend": "rules",
    }


def _load_session(session_id: str) -> Dict[str, Any]:
    p = _session_path(session_id)
    if not p.exists():
        return _new_session(session_id)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _new_session(session_id)


def _save_session(session: Dict[str, Any]) -> None:
    session["updated_at"] = time.time()
    p = _session_path(str(session.get("session_id", "default")))
    p.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")


def _add_history(session: Dict[str, Any], role: str, content: str) -> None:
    session.setdefault("history", []).append({"role": role, "content": content, "ts": time.time()})
    _trim_history(session)


def _extract_ui_languages(text: str) -> list[str]:
    t = (text or "").lower()
    langs: list[str] = []

    def add(code: str) -> None:
        if code not in langs:
            langs.append(code)

    if "english" in t or "anglais" in t:
        add("en")
    if "french" in t or "français" in t or "francais" in t:
        add("fr")
    if "dutch" in t or "nederlands" in t:
        add("nl")
    if "german" in t or "deutsch" in t:
        add("de")
    if "arabic" in t or "arabe" in t:
        add("ar")
    if "tamil" in t:
        add("ta")
    if "spanish" in t or "español" in t or "espagnol" in t:
        add("es")

    return langs


def _guess_product_type(text: str) -> str | None:
    t = text.lower()

    if "mobile app" in t or "android" in t or "ios" in t:
        return "mobile_app"

    if "web app" in t or "webapp" in t:
        return "web_app"

    if " app" in t or t.endswith("app") or "application" in t:
        return "web_app"

    if "dashboard" in t or "admin" in t:
        return "dashboard"

    if "api" in t or "backend" in t:
        return "api_backend"

    if "store" in t or "shop" in t or "e-commerce" in t or "ecommerce" in t:
        return "ecommerce"

    if "site" in t or "website" in t or "landing" in t:
        return "website"

    return None


def _detect_mode_and_security(msg_lower: str) -> tuple[str, str]:
    """
    Decide assistant_mode + security_posture from the goal text.

    Returns:
        (assistant_mode, security_posture)
        assistant_mode: "basic" | "pro" | "architect"
        security_posture: "standard" | "hardened"
    """
    text = msg_lower or ""
    mode = "basic"
    security = "standard"

    # --- Architect triggers: multi-tenant SaaS / complex products ---
    architect_keywords = [
        "multi-tenant",
        "multi tenant",
        "saas",
        "b2b",
        "sso",
        "single sign-on",
        "okta",
        "azure ad",
        "auth0",
        "audit log",
        "audit logs",
        "ip allowlist",
        "ip whitelist",
        "sox",
        "hipaa",
    ]
    if any(kw in text for kw in architect_keywords):
        mode = "architect"

    # --- Pro triggers: dashboards / subscriptions / advanced flows ---
    pro_keywords = [
        "subscription",
        "subscriptions",
        "billing",
        "plans",
        "dashboard",
        "dashboards",
        "kpi",
        "analytics",
        "reporting",
    ]
    if mode == "basic" and any(kw in text for kw in pro_keywords):
        mode = "pro"

    # --- Hardened security triggers ---
    hardened_keywords = [
        "multi-tenant",
        "multi tenant",
        "sso",
        "okta",
        "azure ad",
        "auth0",
        "audit log",
        "audit logs",
        "ip allowlist",
        "ip whitelist",
        "gdpr",
        "pci",
        "hipaa",
        "compliance",
    ]
    if any(kw in text for kw in hardened_keywords):
        security = "hardened"

    return mode, security


def _normalize_platform(product_type: str) -> str:
    if product_type in {"mobile_app"}:
        return "mobile"
    if product_type in {"dashboard", "web_app", "ecommerce", "website"}:
        return "web"
    return "web"


def _canonical_assistant_mode(value: str | None) -> str:
    """
    Normalize assistant_mode to one of: basic | pro | architect.
    Accepts either raw codes or pretty labels.
    """
    text = (value or "").strip().lower()
    if "architect" in text:
        return "architect"
    if "pro" in text:
        return "pro"
    return "basic"


def _canonical_security_posture(value: str | None) -> str:
    """
    Normalize security_posture to: standard | hardened.
    """
    text = (value or "").strip().lower()
    if "hardened" in text:
        return "hardened"
    return "standard"


def _canonical_plan_tier(value: str | None, mode: str, security: str) -> str:
    """
    Normalize / derive plan_tier to: starter | pro | enterprise.
    If explicit value is provided but looks like a label, normalize it.
    Otherwise derive from (mode, security).
    """
    text = (value or "").strip().lower()

    # Try to normalize from explicit value first
    if "enterprise" in text:
        return "enterprise"
    if "pro" in text:
        return "pro"
    if "starter" in text:
        return "starter"

    # Fallback: derive from mode + security
    mode = (mode or "basic").lower()
    security = (security or "standard").lower()

    if mode == "architect" and security == "hardened":
        return "enterprise"
    if mode in {"pro", "architect"}:
        return "pro"
    return "starter"


def _normalize_tier_fields(spec: Dict[str, Any]) -> None:
    raw_mode = spec.get("assistant_mode")
    raw_security = spec.get("security_posture")
    raw_tier = spec.get("plan_tier")

    mode = _canonical_assistant_mode(raw_mode)
    security = _canonical_security_posture(raw_security)
    tier = _canonical_plan_tier(raw_tier, mode, security)

    spec["assistant_mode"] = mode
    spec["security_posture"] = security
    spec["plan_tier"] = tier

    if tier == "enterprise":
        db = (spec.get("database") or "").strip().lower()
        if not db or db == "sqlite":
            spec["database"] = "postgres"

    plugins = list(spec.get("plugins") or [])
    compliance = list(spec.get("compliance") or [])

    if tier == "starter":
        plugins = [p for p in plugins if p not in {"subscriptions", "billing"}]
        compliance = [c for c in compliance if c.lower() not in {"multi_tenant"}]

    elif tier == "pro":
        if "auth" not in plugins:
            plugins.append("auth")
        compliance = [c for c in compliance if c.lower() not in {"multi_tenant"}]

    elif tier == "enterprise":
        for p in ("auth", "subscriptions", "billing"):
            if p not in plugins:
                plugins.append(p)
        lowered = [c.lower() for c in compliance]
        if "multi_tenant" not in lowered:
            compliance.append("multi_tenant")

    if plugins:
        spec["plugins"] = plugins
    if compliance:
        spec["compliance"] = compliance


def _default_frontend(platform: str) -> str:
    if platform == "mobile":
        return "flutter"
    return "nextjs"


def _default_backend() -> str:
    return "fastapi"


def _default_database() -> str:
    return "sqlite"


def _slug_from_goal(goal: str) -> str:
    base = "".join(c.lower() if c.isalnum() else "_" for c in goal) or "app"
    while "__" in base:
        base = base.replace("__", "_")
    return base.strip("_")[:32] or "app"


LANG_NAME_TO_CODE = {
    "english": "en",
    "en": "en",
    "french": "fr",
    "français": "fr",
    "fr": "fr",
    "dutch": "nl",
    "nederlands": "nl",
    "nl": "nl",
    "german": "de",
    "deutsch": "de",
    "de": "de",
    "arabic": "ar",
    "ar": "ar",
    "tamil": "ta",
    "ta": "ta",
    "spanish": "es",
    "es": "es",
    "portuguese": "pt",
    "pt": "pt",
    "italian": "it",
    "it": "it",
    "turkish": "tr",
    "tr": "tr",
    "hindi": "hi",
    "hi": "hi",
    "chinese": "zh",
    "zh": "zh",
}


def _extract_ui_languages(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for name, code in LANG_NAME_TO_CODE.items():
        if len(name) <= 3:
            patterns = [
                " " + name + " ",
                " " + name + ",",
                " " + name + ".",
                " " + name + " and",
                "(" + name + ")",
                "[" + name + "]",
            ]
            if any(p in lower for p in patterns):
                if code not in found:
                    found.append(code)
        else:
            if name in lower and code not in found:
                found.append(code)
    return found


def _spec_summary(spec: Dict[str, Any]) -> str:
    product_type = spec.get("product_type", "product")
    goal = spec.get("goal", "not specified yet")
    features = spec.get("main_features") or []
    pages = spec.get("pages") or []
    target_users = spec.get("target_users", "not specified")
    design_style = spec.get("design_style", "not specified")

    frontend = spec.get("frontend") or _default_frontend(spec.get("platform") or "web")
    backend = spec.get("backend") or _default_backend()
    database = spec.get("database") or _default_database()
    module_name = spec.get("module_name") or _slug_from_goal(goal)

    roles = spec.get("roles") or []
    user_flows = spec.get("user_flows") or []
    plugins = spec.get("plugins") or []
    compliance = spec.get("compliance") or []
    ui_languages = spec.get("ui_languages") or spec.get("locales") or []

    assistant_mode = (spec.get("assistant_mode") or "basic").lower()
    security_posture = (spec.get("security_posture") or "standard").lower()
    plan_tier = (
        spec.get("plan_tier") or _derive_plan_tier(assistant_mode, security_posture)
    ).lower()

    assistant_mode_label_map = {
        "basic": "Basic (guided wizard)",
        "pro": "Pro (advanced planner)",
        "architect": "Architect (SaaS / multi-tenant aware)",
    }
    security_posture_label_map = {
        "standard": "Standard (good secure defaults)",
        "hardened": "Hardened (audit logs, IP allowlist, stricter defaults)",
    }
    plan_tier_label_map = {
        "starter": "Starter – simple projects",
        "pro": "Pro – advanced features",
        "enterprise": "Enterprise – architect + hardened security",
    }

    assistant_mode_label = assistant_mode_label_map.get(assistant_mode, assistant_mode)
    security_posture_label = security_posture_label_map.get(security_posture, security_posture)
    plan_tier_label = plan_tier_label_map.get(plan_tier, plan_tier)

    features_str = ", ".join(features) if features else "not specified"
    pages_str = ", ".join(pages) if pages else "Home"
    roles_str = ", ".join(roles) if roles else "standard users"
    flows_str = "; ".join(user_flows) if user_flows else "not specified"
    plugins_str = ", ".join(plugins) if plugins else "not specified"
    compliance_str = ", ".join(compliance) if compliance else "none specified"
    ui_languages = spec.get("ui_languages") or []
    ui_langs_str = ", ".join(ui_languages) if ui_languages else "not specified"
    return (
        "Here is what I understood so far:\n\n"
        f"- Product type: {product_type}\n"
        f"- Main goal: {goal}\n"
        f"- Main features: {features_str}\n"
        f"- Pages: {pages_str}\n"
        f"- Target users: {target_users}\n"
        f"- Roles: {roles_str}\n"
        f"- User flows: {flows_str}\n"
        f"- Feature plugins: {plugins_str}\n"
        f"- Compliance: {compliance_str}\n"
        f"- Assistant mode: {assistant_mode_label}\n"
        f"- Security posture: {security_posture_label}\n"
        f"- Plan tier: {plan_tier_label}\n"
        f"- UI languages: {ui_langs_str}\n"
        f"- Style: {design_style}\n"
        f"- Tech stack (for developers): frontend={frontend}, backend={backend}, database={database}\n"
        f"- Project name / module: {module_name}" + _repo_context_lines(spec)
    )


def _repo_context_lines(spec: Dict[str, Any]) -> str:
    rs = spec.get("repo_summary") or {}
    if not isinstance(rs, dict) or not rs.get("ok"):
        return ""
    stats = rs.get("stats") or {}
    total = stats.get("total_files_seen")
    top_langs = rs.get("top_languages") or []
    top_dirs = stats.get("top_dirs") or {}
    # keep it short
    dirs_sorted = sorted(top_dirs.items(), key=lambda kv: kv[1], reverse=True)[:5]
    dirs_txt = ", ".join([f"{k}({v})" for k, v in dirs_sorted]) if dirs_sorted else "n/a"
    langs_txt = ", ".join(top_langs[:5]) if top_langs else "n/a"
    return (
        "\n\nRepo context (auto):\n"
        f"- Total files: {total}\n"
        f"- Top dirs: {dirs_txt}\n"
        f"- Top languages: {langs_txt}"
    )


def _apply_spec_edits_from_text(spec: Dict[str, Any], msg_lower: str) -> bool:
    changed = False
    if not msg_lower:
        return False

    features = list(spec.get("main_features") or [])
    pages = list(spec.get("pages") or [])

    original_features = list(features)
    original_pages = list(pages)

    if "dark mode" in msg_lower or "make it darker" in msg_lower or "dark theme" in msg_lower:
        spec["design_style"] = "dark mode"
        changed = True
    if "light mode" in msg_lower or "make it lighter" in msg_lower or "minimal" in msg_lower:
        if "dark" not in msg_lower:
            spec["design_style"] = "clean and minimal"
            changed = True

    if "add payment" in msg_lower or "payments" in msg_lower or "stripe" in msg_lower:
        if "payments" not in features:
            features.append("payments")
            changed = True

    if "admin page" in msg_lower or "add admin" in msg_lower or "admin panel" in msg_lower:
        if not any(p.lower() == "admin" for p in pages):
            pages.append("Admin")
            changed = True

    if "dashboard" in msg_lower and not any(p.lower() == "dashboard" for p in pages):
        pages.append("Dashboard")
        changed = True

    if "backend" in msg_lower and "fastapi" in msg_lower:
        if spec.get("backend") != "fastapi":
            spec["backend"] = "fastapi"
            changed = True
    if "backend" in msg_lower and "node" in msg_lower:
        if spec.get("backend") != "node":
            spec["backend"] = "node"
            changed = True
    if "backend" in msg_lower and "django" in msg_lower:
        if spec.get("backend") != "django":
            spec["backend"] = "django"
            changed = True

    if "frontend" in msg_lower and "next" in msg_lower:
        if spec.get("frontend") != "nextjs":
            spec["frontend"] = "nextjs"
            changed = True
    if "frontend" in msg_lower and "react" in msg_lower and "react native" not in msg_lower:
        if spec.get("frontend") != "react":
            spec["frontend"] = "react"
            changed = True
    if "frontend" in msg_lower and "vue" in msg_lower:
        if spec.get("frontend") != "vue":
            spec["frontend"] = "vue"
            changed = True

    if "postgres" in msg_lower or "postgresql" in msg_lower:
        if spec.get("database") != "postgres":
            spec["database"] = "postgres"
            changed = True
    if "mysql" in msg_lower:
        if spec.get("database") != "mysql":
            spec["database"] = "mysql"
            changed = True
    if "mongo" in msg_lower:
        if spec.get("database") != "mongodb":
            spec["database"] = "mongodb"
            changed = True
    if "sqlite" in msg_lower:
        if spec.get("database") != "sqlite":
            spec["database"] = "sqlite"
            changed = True

    if "mobile app" in msg_lower or "android app" in msg_lower or "ios app" in msg_lower:
        if spec.get("product_type") != "mobile_app":
            spec["product_type"] = "mobile_app"
            spec["platform"] = "mobile"
            if spec.get("frontend") in {None, "", "nextjs", "react"}:
                spec["frontend"] = "flutter"
            changed = True

    if features != original_features:
        spec["main_features"] = features
    if pages != original_pages:
        spec["pages"] = pages

    return changed


def _project_summary_or_empty(session: Dict[str, Any]) -> str:
    spec = session.get("spec") or {}
    if not spec.get("product_type"):
        return ""
    return _spec_summary(spec)


def _start_build(session: Dict[str, Any]) -> str:
    spec: Dict[str, Any] = session.setdefault("spec", {})

    idea = spec.get("goal") or "New Velu app"
    module = spec.get("module_name") or "app_mod"
    frontend = spec.get("frontend") or _default_frontend(spec.get("platform") or "web")
    backend = spec.get("backend") or _default_backend()
    database = spec.get("database") or _default_database()
    kind = spec.get("product_type") or "app"

    mode = spec.get("assistant_mode")
    security = spec.get("security_posture")
    plan_tier = spec.get("plan_tier") or _derive_plan_tier(mode, security)
    plugins = list(spec.get("plugins") or [])
    ui_languages = list(spec.get("ui_languages") or [])

    session_id = str(session.get("session_id") or module)
    repo_ctx = _compute_repo_summary_for_spec(spec)
    if repo_ctx:
        spec["repo_summary"] = repo_ctx  # persists into the session

    intake_payload: Dict[str, Any] = {
        "kind": kind,
        "idea": idea,
        "frontend": frontend,
        "backend": backend,
        "database": database,
        "module": module,
        "schema": {},
        "session_id": session_id,
        "plan_tier": plan_tier,
        "plugins": plugins,
        "ui_languages": ui_languages,
        "repo_summary": repo_ctx,  # may be None
    }

    intake_job_id = q.enqueue(task="intake", payload=intake_payload)

    jobs = session.setdefault("jobs", {})
    jobs["intake"] = intake_job_id

    if os.getenv("VELU_ENABLE_PACKAGER") == "1":
        try:
            packager_payload: Dict[str, Any] = {
                "module": module,
                "kind": kind,
                "backend": backend,
                "database": database,
                "plan_tier": plan_tier,
                "plugins": plugins,
            }
            packager_job_id = q.enqueue(
                task="packager",
                payload=packager_payload,
                priority=0,
            )
            jobs["packager"] = packager_job_id
        except Exception as exc:
            logger.warning("chat: failed to enqueue packager: %s", exc)

    session["stage"] = "building"

    return (
        "Perfect, I’m starting the build now.\n\n"
        f"- Planning + build job: #{intake_job_id}\n\n"
        "You can watch this job in the Velu queue tab.\n"
        "Once it finishes, your code and tests will be available in the repo.\n\n"
        "When you later run the packaged project, the backend API will usually "
        "listen on port 8000 and the web frontend on port 3000 or 3001. "
        "The Help tab in the console shows the exact commands."
    )


def _run_rules_backend(session: Dict[str, Any], msg: str) -> str:
    return _next_question(session, msg)


def _call_local_llm(session: Dict[str, Any], msg: str) -> str:
    return _next_question(session, msg)


def _call_remote_llm(session: Dict[str, Any], msg: str) -> str:
    draft_reply = _next_question(session, msg)

    try:
        system_prompt = (
            "You are Velu, an AI assistant that helps users design small apps and websites.\n"
            "You are given an INTERNAL builder reply produced by deterministic rules.\n"
            "Rewrite that internal reply so it is clear, friendly, and helpful,\n"
            "WITHOUT changing its meaning or instructions.\n"
            "Do not add new requirements or contradict the internal reply.\n"
        )

        user_prompt = (
            f"User message:\n{msg or '[empty]'}\n\n"
            f"Internal builder reply (draft):\n{draft_reply}\n\n"
            "Rewrite the internal builder reply in a clearer, more natural tone.\n"
            "Keep all steps, examples, and instructions.\n"
            "Return ONLY the rewritten message text."
        )

        text = llm_client.remote_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        ).strip()

        if not text:
            return draft_reply
        return text
    except Exception as e:
        return draft_reply + (
            f"\n\n(Note: remote LLM backend failed with error: {e!s}. "
            "Using the basic rules flow for now.)"
        )


def _run_hospital_command(session: Dict[str, Any], user_message: str) -> str:
    msg_lower = (user_message or "").lower().strip()

    if msg_lower in {"hospital", "hospital help"}:
        return (
            "Hospital mode commands:\n"
            '- "hospital analyze" or "hospital build"\n\n'
            "These will run a hospital-specific codegen/analysis job over:\n"
            "- team_dashboard_api.py\n"
            "- tests/test_team_dashboard_api.py\n\n"
            "You can then inspect the job result in the Velu queue tab."
        )

    if msg_lower.startswith("hospital "):
        cmd = msg_lower.split(" ", 1)[1].strip()
    else:
        cmd = ""

    if cmd in {"analyze", "build", "codegen"}:
        spec: Dict[str, Any] = {
            "project": {
                "name": "hospital_demo",
                "type": "web_app",
            },
            "stack": {
                "frontend": {"framework": "nextjs", "language": "typescript"},
                "backend": {"framework": "fastapi", "language": "python"},
                "database": {"engine": "sqlite", "mode": "single_tenant"},
            },
            "features": {
                "modules": ["patients", "appointments", "doctors", "dashboard"],
            },
        }
        payload: Dict[str, Any] = {
            "spec": spec,
            "apply": True,
            "target_files": [
                "team_dashboard_api.py",
                "tests/test_team_dashboard_api.py",
            ],
        }
        job_id = q.enqueue(
            task="hospital_codegen",
            payload=payload,
            priority=0,
        )

        jobs = session.setdefault("jobs", {})
        jobs["hospital_codegen"] = job_id

        return (
            "Started a hospital codegen/analysis job.\n\n"
            f"- Task: hospital_codegen\n"
            f"- Job id: #{job_id}\n\n"
            "You can open the Velu queue tab, find this job, and inspect the\n"
            "analysis + prepared patches for the hospital API and its tests."
        )

    return (
        "I didn’t recognize that hospital command.\n\n"
        "Available commands:\n"
        '- "hospital analyze"\n'
        '- "hospital build"\n'
        '- "hospital help"'
    )


def _update_spec_from_freeform(
    spec: Dict[str, Any], msg: str, msg_lower: str, skip_features: bool = False
) -> bool:
    changed = False

    backend = spec.get("backend") or ""
    frontend = spec.get("frontend") or ""
    database = spec.get("database") or ""
    features = list(spec.get("main_features") or [])
    plugins = list(spec.get("plugins") or [])

    # -----------------------
    # Backend choice
    # -----------------------
    new_backend = None
    if "fastapi" in msg_lower:
        new_backend = "fastapi"
    elif "django" in msg_lower:
        new_backend = "django"
    elif "express" in msg_lower:
        new_backend = "express"
    elif "nestjs" in msg_lower:
        new_backend = "nestjs"
    elif "node" in msg_lower:
        new_backend = "node"
    elif "laravel" in msg_lower:
        new_backend = "laravel"
    elif "spring boot" in msg_lower or "spring" in msg_lower:
        new_backend = "spring_boot"
    elif "go backend" in msg_lower or "golang" in msg_lower:
        new_backend = "go"

    if "no backend" in msg_lower or "frontend only" in msg_lower:
        new_backend = "none"

    if new_backend and new_backend != backend:
        spec["backend"] = new_backend
        changed = True

    # -----------------------
    # Frontend choice
    # -----------------------
    new_frontend = None
    if "next.js" in msg_lower or "nextjs" in msg_lower or "next js" in msg_lower:
        new_frontend = "nextjs"
    elif "react spa" in msg_lower or "vite" in msg_lower:
        new_frontend = "react"
    elif "vue" in msg_lower:
        new_frontend = "vue"
    elif "sveltekit" in msg_lower or "svelte" in msg_lower:
        new_frontend = "sveltekit"
    elif "react native" in msg_lower:
        new_frontend = "react_native"
    elif "expo" in msg_lower:
        new_frontend = "expo"
    elif "flutter" in msg_lower:
        new_frontend = "flutter"
    elif "no frontend" in msg_lower or "api only" in msg_lower:
        new_frontend = "none"

    if new_frontend and new_frontend != frontend:
        spec["frontend"] = new_frontend
        changed = True

    # -----------------------
    # Database choice
    # -----------------------
    new_db = None
    if "postgresql" in msg_lower or "postgres" in msg_lower:
        new_db = "postgres"
    elif "mysql" in msg_lower:
        new_db = "mysql"
    elif "mongo" in msg_lower or "mongodb" in msg_lower:
        new_db = "mongodb"
    elif "sqlite" in msg_lower:
        new_db = "sqlite"
    elif "no database" in msg_lower or "no db" in msg_lower:
        new_db = "none"

    if new_db and new_db != database:
        spec["database"] = new_db
        changed = True

    # -----------------------
    # High-level features
    # -----------------------
    def _add_feature(label: str) -> None:
        nonlocal changed
        if label not in features:
            features.append(label)
            changed = True

    if not skip_features:

        if any(w in msg_lower for w in ["payment", "payments", "stripe", "checkout"]):
            _add_feature("payments")

        if any(w in msg_lower for w in ["admin", "backoffice", "admin panel"]):
            _add_feature("admin dashboard")

        if "dashboard" in msg_lower and "dashboard" not in " ".join(features).lower():
            _add_feature("dashboard")

        if "search" in msg_lower and "search" not in " ".join(features).lower():
            _add_feature("search")

        if any(w in msg_lower for w in ["upload", "file upload", "uploads"]):
            _add_feature("file uploads")

        if any(
            w in msg_lower
            for w in ["multilingual", "multi language", "multi-language", "multi language ui"]
        ):
            _add_feature("multi-language ui")

        if changed and not skip_features:
            spec["main_features"] = features

    # -----------------------
    # Plugins (capability bricks)
    # -----------------------
    def _add_plugin(slug: str) -> None:
        nonlocal changed
        if slug not in plugins:
            plugins.append(slug)
            changed = True

    if any(word in msg_lower for word in ["login", "sign in", "signup", "auth", "authentication"]):
        _add_plugin("auth")

    if any(word in msg_lower for word in ["blog", "articles", "posts"]):
        _add_plugin("blog")

    if any(
        word in msg_lower
        for word in ["store", "shop", "checkout", "cart", "ecommerce", "e-commerce"]
    ):
        _add_plugin("ecommerce")

    if any(word in msg_lower for word in ["subscription", "subscriptions", "plans", "billing"]):
        _add_plugin("billing")

    if any(
        word in msg_lower
        for word in ["notification", "email alerts", "push notification", "webpush"]
    ):
        _add_plugin("notifications")

    if changed:
        spec["plugins"] = plugins

    # -----------------------
    # Roles & permissions
    # -----------------------
    roles = list(spec.get("roles") or [])

    def _ensure_role(name: str) -> None:
        nonlocal changed
        norm = name.strip()
        if not norm:
            return
        if norm.lower() not in [r.lower() for r in roles]:
            roles.append(norm)
            changed = True

    # Explicit "roles: admin, manager, staff" pattern
    if "roles:" in msg_lower:
        idx = msg_lower.find("roles:")
        raw_roles = msg[idx + len("roles:") :]  # noqa: F841
        # Use original msg slice to preserve capitalization
        original_slice = msg[idx + len("roles:") :]
        for part in original_slice.replace(" and ", ",").split(","):
            label = part.strip(" .:")
            if label:
                _ensure_role(label.title())

    # Heuristic roles from common role words
    known_role_words = [
        "admin",
        "manager",
        "staff",
        "employee",
        "customer",
        "client",
        "tenant",
        "agent",
    ]
    for word in known_role_words:
        if word in msg_lower:
            _ensure_role(word.title())

    if roles:
        spec["roles"] = roles

    # -----------------------
    # User flows / journeys
    # -----------------------
    user_flows = list(spec.get("user_flows") or [])

    def _ensure_flow(flow: str) -> None:
        nonlocal changed
        norm = " ".join(flow.split())
        if not norm:
            return
        if norm.lower() not in [f.lower() for f in user_flows]:
            user_flows.append(norm)
            changed = True

    # Explicit "flow:" / "journey:" snippets
    for marker in ["flow:", "journey:", "user flow:", "user journey:"]:
        if marker in msg_lower:
            idx = msg_lower.find(marker)
            original_slice = msg[idx + len(marker) :]
            # Allow multiple flows separated by ";" or newline
            for part in original_slice.replace("\n", ";").split(";"):
                txt = part.strip(" .")
                if txt:
                    _ensure_flow(txt)

    # Simple heuristics: “as a X I want to Y”
    if "as a " in msg_lower and " i want " in msg_lower:
        # crude but works for many sentences
        try:
            start = msg_lower.index("as a ")
            fragment = msg[start:]
            # Cut at sentence end
            for sep in [".", "!", "?"]:
                if sep in fragment:
                    fragment = fragment.split(sep, 1)[0]
            _ensure_flow(fragment.strip().capitalize())
        except Exception:
            logger.debug(
                "chat: failed to ensure flow for fragment %r",
                fragment,
                exc_info=True,
            )
            pass

    if user_flows:
        spec["user_flows"] = user_flows

    # -----------------------
    # Compliance / regimes
    # -----------------------
    compliance = list(spec.get("compliance") or [])

    def _ensure_compliance(tag: str) -> None:
        nonlocal changed
        norm = tag.strip()
        if not norm:
            return
        if norm.lower() not in [c.lower() for c in compliance]:
            compliance.append(norm)
            changed = True

    if "gdpr" in msg_lower or "europe data" in msg_lower or "eu only" in msg_lower:
        _ensure_compliance("GDPR")

    if "hipaa" in msg_lower or "health data" in msg_lower or "medical data" in msg_lower:
        _ensure_compliance("HIPAA-like")

    if "pci" in msg_lower or "card data" in msg_lower:
        _ensure_compliance("PCI")

    if compliance:
        spec["compliance"] = compliance
    ui_langs = list(spec.get("ui_languages") or [])

    def _ensure_lang(code: str) -> None:
        nonlocal changed
        c = code.strip()
        if not c:
            return
        if c.lower() not in [l.lower() for l in ui_langs]:  # noqa: E741
            ui_langs.append(c)
            changed = True

        lang_map = {
            "english": "en",
            "en": "en",
            "french": "fr",
            "fr": "fr",
            "dutch": "nl",
            "nl": "nl",
            "german": "de",
            "de": "de",
            "arabic": "ar",
            "ar": "ar",
            "tamil": "ta",
            "ta": "ta",
            "spanish": "es",
            "es": "es",
            "portuguese": "pt",
            "pt": "pt",
            "italian": "it",
            "it": "it",
            "turkish": "tr",
            "tr": "tr",
        }
        marker_idx = -1
        for marker in ["ui languages:", "languages:", "locales:"]:
            idx = msg_lower.find(marker)
            if idx != -1:
                marker_idx = idx
                break
        if marker_idx != -1:
            original_slice = msg[marker_idx:]
            for sep in [":", "-", "="]:
                if sep in original_slice:
                    original_slice = original_slice.split(sep, 1)[1]
                    break
            for part in original_slice.replace(" and ", ",").split(","):
                label = part.strip().lower()
                if not label:
                    continue
                for key, code in lang_map.items():
                    if key in label:
                        _ensure_lang(code)
        for key, code in lang_map.items():
            if key in msg_lower:
                _ensure_lang(code)
        if ui_langs:
            spec["ui_languages"] = ui_langs

        langs = _extract_ui_languages(msg)
        if langs:
            existing = list(spec.get("ui_languages") or spec.get("locales") or [])
            have = set(existing)
            updated = list(existing)
            for code in langs:
                if code not in have:
                    updated.append(code)
                    have.add(code)
                    changed = True
            if updated:
                spec["ui_languages"] = updated
                spec["locales"] = updated

    return changed


def _parse_goal_block_into_spec(spec: Dict[str, Any], text: str) -> bool:
    """
    Pull structured info out of a rich goal paragraph and merge into spec:
    - roles: list[str]
    - user_flows: list[str]
    - plugins: inferred feature plugins
    - compliance: list[str] like ["GDPR", "multi_tenant"]
    Also calls _update_spec_from_freeform(..., skip_features=True) to pick up
    backend/frontend/db and plugins without touching main_features.
    """
    changed = False
    if not text:
        return False

    lower = text.lower()

    # --- Roles block ---
    roles: list[str] = list(spec.get("roles") or [])
    if "roles:" in lower:
        start = lower.index("roles:")
        end = len(text)
        for marker in ["flows:", "we need", "security:", "tech preferences:", "tech preference:"]:
            idx = lower.find(marker, start)
            if idx != -1:
                end = min(end, idx)
        roles_block = text[start + len("roles:") : end].strip()
        raw_roles = [r.strip() for r in roles_block.replace("\n", " ").split(",") if r.strip()]
        for r in raw_roles:
            if r and r not in roles:
                roles.append(r)
                changed = True
    if roles:
        spec["roles"] = roles

    # --- Flows block ---
    user_flows: list[str] = list(spec.get("user_flows") or [])
    if "flows:" in lower:
        start = lower.index("flows:")
        end = len(text)
        for marker in ["we need", "security:", "tech preferences:", "tech preference:"]:
            idx = lower.find(marker, start)
            if idx != -1:
                end = min(end, idx)
        flows_block = text[start + len("flows:") : end].strip()
        for line in flows_block.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("-"):
                line = line[1:].strip()
            if line and line not in user_flows:
                user_flows.append(line)
                changed = True
    if user_flows:
        spec["user_flows"] = user_flows

    # --- Plugins / compliance flags from whole text ---
    plugins: list[str] = list(spec.get("plugins") or [])
    compliance_tags: list[str] = list(spec.get("compliance") or [])

    def _ensure_plugin(slug: str) -> None:
        nonlocal changed
        if slug not in plugins:
            plugins.append(slug)
            changed = True

    def _ensure_compliance(tag: str) -> None:
        nonlocal changed
        norm = tag.strip()
        if not norm:
            return
        if norm not in compliance_tags and norm.upper() not in [c.upper() for c in compliance_tags]:
            compliance_tags.append(norm)
            changed = True

    if any(w in lower for w in ["login", "sign in", "signup", "auth"]):
        _ensure_plugin("auth")
    if "subscription" in lower or "subscriptions" in lower or "plans" in lower:
        _ensure_plugin("subscriptions")
        _ensure_plugin("billing")
    if "gdpr" in lower:
        _ensure_compliance("GDPR")
    if "multi-tenant" in lower or "multi tenant" in lower:
        _ensure_compliance("multi_tenant")

    if plugins:
        spec["plugins"] = plugins
    if compliance_tags:
        spec["compliance"] = compliance_tags

    # Also let the generic parser fill backend/frontend/db/etc,
    # but DO NOT touch main_features at this stage.
    if _update_spec_from_freeform(spec, text, lower, skip_features=True):
        changed = True

    return changed


def _load_job_result(job_id: int | None) -> dict[str, Any] | None:
    if not job_id:
        return None
    try:
        rec = jobs_sqlite.load(int(job_id))
        if not rec:
            return None
        if rec.get("status") != "done":
            return None
        return rec.get("result")  # already decoded by jobs_sqlite in this repo
    except Exception:
        return None


def _enqueue_repo_summary(session: Dict[str, Any]) -> int:
    payload = {
        "root": ".",
        "focus_dirs": ["services", "tests", "src"],
        "include_snippets": False,  # keep safe default
    }
    jid = q.enqueue(task="repo_summary", payload=payload, priority=0)
    session.setdefault("jobs", {})["repo_summary"] = jid
    return jid


def _next_question(session: Dict[str, Any], user_message: str) -> str:
    spec: Dict[str, Any] = session.setdefault("spec", {})
    _maybe_attach_repo_summary_result(session)
    _maybe_enqueue_repo_summary(session)

    msg = (user_message or "").strip()
    msg_lower = msg.lower().strip()
    # Repo analysis command (safe)
    if msg_lower in {"analyze repo", "repo summary", "analyze repository"}:
        jid = _enqueue_repo_summary(session)
        return (
            f"Started repo analysis (repo_summary).\n\n"
            f"- Job id: #{jid}\n\n"
            "Open the Velu queue tab and watch that job.\n"
            "When it finishes, I will use the repo context in planning."
        )

    summary: str = ""

    if msg_lower in {"use repo", "use repo summary", "repo summary on"}:
        spec["use_repo_summary"] = True
        spec.setdefault("repo_root", ".")
        return "Okay — I’ll analyze the repo and use it to improve planning. Ask me a question or say 'build' when ready."

    if msg_lower.startswith("hospital"):
        return _run_hospital_command(session, msg)

    if msg_lower in {"repo", "repo summary", "analyze repo", "analyse repo"}:
        # enqueue a safe repo scan (no snippets by default)
        payload = {
            "root": ".",
            "focus_dirs": ["services", "tests", "src", "generated"],
            "include_snippets": False,
        }
        job_id = q.enqueue(task="repo_summary", payload=payload, priority=0)
        session.setdefault("jobs", {})["repo_summary"] = job_id
        return (
            f"Started repo_summary.\n\n"
            f"- Job id: #{job_id}\n\n"
            "Type `repo` again in a few seconds to show the results, "
            "or open the Queue tab and watch the job."
        )

    # If we already have a repo_summary job, allow user to fetch it
    if msg_lower in {"repo status", "repo results"}:
        jobs = session.setdefault("jobs", {})
        rid = jobs.get("repo_summary")
        rec = _get_job_full(rid) if rid else None
        if not rec:
            return "No repo_summary job tracked yet. Type `repo` to start one."
        if rec.get("status") in {"queued", "running"}:
            return f"repo_summary is still running (job #{rid})."
        if rec.get("status") == "error":
            return f"repo_summary failed (job #{rid})."
        result_obj = rec.get("result") or {}
        return _format_repo_summary_for_assistant(result_obj)
        # OPTIONAL: if user hasn't chosen backend yet, suggest based on dominant repo language
        if rec.get("status") == "done":
            result_obj = rec.get("result") or {}
            langs = result_obj.get("languages") or {}
            spec = session.setdefault("spec", {})

            if not spec.get("backend"):
                # simple heuristic
                if (langs.get("Python") or 0) >= (langs.get("JavaScript") or 0) and (
                    langs.get("Python") or 0
                ) > 0:
                    spec["backend"] = "fastapi"
                elif (langs.get("TypeScript") or 0) > 0 or (langs.get("JavaScript") or 0) > 0:
                    spec["backend"] = "node"

    if msg_lower in {"build", "go", "start", "generate", "yes"} and spec.get("module_name"):
        stage = session.get("stage") or "collecting"
        if stage in {"collecting", "ready_to_build", "done"}:
            return _start_build(session)

    if session.get("stage") == "building":
        spec = session.setdefault("spec", {})
        jobs = session.setdefault("jobs", {})
        intake_job = jobs.get("intake")

        job = _get_job(intake_job) if intake_job else None
        status = (job or {}).get("status")

        is_build_cmd = msg_lower in {"build", "go", "start", "generate", "yes"}
        is_status_cmd = msg_lower in {"status", "progress", "build status"}

        if is_build_cmd or is_status_cmd:
            if intake_job and status in {"queued", "running", None}:
                return (
                    f"Your build is still running (job #{intake_job}).\n\n"
                    "You can open the Velu queue tab and click “Watch” on that job "
                    "to follow the logs and progress."
                )

            if intake_job and status == "done":
                session["stage"] = "done"
                return (
                    f"Your build has finished successfully (job #{intake_job}).\n\n"
                    "You can now explore the generated code under:\n"
                    "- `generated/services`  (backend / FastAPI)\n"
                    "- `generated/web`       (frontend / Next.js)\n\n"
                    "Example to run the backend locally:\n"
                    "```bash\n"
                    "uvicorn generated.services.api.app:app --reload --port 9001\n"
                    "```\n\n"
                    "Example to run the frontend locally:\n"
                    "```bash\n"
                    "cd generated/web\n"
                    "npm install\n"
                    "npm run dev -- --port 3001\n"
                    "```\n"
                    "Then open http://localhost:3001 in your browser."
                )

            if intake_job and status == "error":
                session["stage"] = "ready_to_build"
                summary = _spec_summary(spec)
                return (
                    summary + "\n\n"
                    f"The last build (job #{intake_job}) **failed**.\n"
                    "You can tweak the description or requirements, then reply "
                    '"build" again to start a new attempt.'
                )

            session["stage"] = "ready_to_build"
            summary = _spec_summary(spec)
            return (
                summary + "\n\n"
                "I don’t see an active build job anymore.\n"
                'If you want to generate code again, reply with "build".'
            )

        summary = _spec_summary(spec)
        # If repo_summary finished, attach it into spec so planning can use it
        repo_jid = (session.get("jobs") or {}).get("repo_summary")
        repo_result = _load_job_result(repo_jid)
        if repo_result:
            spec["repo_context"] = repo_result

        if intake_job and status in {"queued", "running", None}:
            return (
                summary + "\n\n"
                f"A build is currently running as job #{intake_job}.\n"
                "You can:\n"
                "- Check the Velu queue tab and watch that job, or\n"
                '- Ask me "status" to check progress again.'
            )

        if intake_job and status == "done":
            session["stage"] = "done"
            return (
                summary + "\n\n"
                f"Good news: the latest build (job #{intake_job}) is finished.\n"
                "You can run it locally as described above, or tell me what you’d "
                "like to change for the next version."
            )

        if intake_job and status == "error":
            session["stage"] = "ready_to_build"
            return (
                summary + "\n\n"
                f"The last build (job #{intake_job}) failed.\n"
                "Describe what you’d like to adjust or fix, then reply "
                '"build" to try again with the updated spec.'
            )

        session["stage"] = "ready_to_build"
        return (
            summary + "\n\n"
            "I don’t see a tracked build job for this session anymore.\n"
            'If you want, you can start a new build by replying "build".'
        )

    if "product_type" not in spec:
        guessed = _guess_product_type(msg)
        if guessed:
            spec["product_type"] = guessed
            session["stage"] = "collecting"
            return (
                f"Great, we’ll build a {guessed.replace('_', ' ')}.\n"
                "What is the main goal of this product? For example: "
                '"sell shoes online" or "show my products" or '
                '"simple website for my company".'
            )
        return (
            "Hi, I’ll help you create your app or website.\n\n"
            "First question: what do you want to build?\n"
            "- Website\n"
            "- Web app\n"
            "- Mobile app\n"
            "- Dashboard\n"
            "- Online store\n\n"
            "You can answer in your own words, for example: "
            '"a simple website to show my products".'
        )

    if "goal" not in spec:
        if msg:
            spec["goal"] = msg
            msg_lower_full = msg.lower().strip()

            mode, security = _detect_mode_and_security(msg_lower_full)

            current_mode = (spec.get("assistant_mode") or "basic").lower()
            current_sec = (spec.get("security_posture") or "standard").lower()

            if current_mode == "basic":
                spec["assistant_mode"] = mode
            else:
                spec.setdefault("assistant_mode", mode)

            if current_sec == "standard":
                spec["security_posture"] = security
            else:
                spec.setdefault("security_posture", security)

            spec["plan_tier"] = _derive_plan_tier(
                spec.get("assistant_mode"),
                spec.get("security_posture"),
            )

            _parse_goal_block_into_spec(spec, msg)
            _update_spec_from_freeform(spec, msg, msg_lower, skip_features=True)

            langs = _extract_ui_languages(msg)
            if langs:
                spec["ui_languages"] = langs

            return (
                "Got it.\n\n"
                "What are the most important things this product should do?\n"
                "You can list features separated by commas. Example:\n"
                '"show products, contact form, search, admin page".'
            )

    if "main_features" not in spec:
        if msg:
            features = [s.strip() for s in msg.split(",") if s.strip()]
            spec["main_features"] = features or ["core features"]
            return (
                "Nice.\n\n"
                "Which pages do you want on this product?\n"
                "For example: Home, Products, About, Contact."
            )
        return (
            "List a few features, separated by commas.\n"
            "Example: login, profile page, search, payments."
        )

    if "pages" not in spec:
        if msg:
            pages = [s.strip() for s in msg.split(",") if s.strip()]
            spec["pages"] = pages or ["Home"]
            return (
                "Great.\n\n"
                "Who will use this most? For example:\n"
                '"customers", "internal team", "admins", "managers".'
            )
        return (
            "Tell me the page names you want (Home, Products, About, Contact, etc.), "
            "separated by commas."
        )

    if "target_users" not in spec:
        if msg:
            spec["target_users"] = msg
            product_type = spec["product_type"]
            platform = _normalize_platform(product_type)
            spec["platform"] = platform
            return (
                f"Great. I’ll treat this as a {platform} product.\n\n"
                "What kind of visual style do you prefer?\n"
                'Examples: "clean and minimal", "colorful", "dark mode", "simple and friendly".'
            )
        return "Who is this mainly for? Customers, employees, or someone else?"

    if "design_style" not in spec:
        if msg:
            spec["design_style"] = msg
            platform = spec.get("platform") or "web"
            spec["frontend"] = _default_frontend(platform)
            spec["backend"] = _default_backend()
            spec["database"] = _default_database()
            return (
                "Nice.\n\n"
                "For the technical part (for developers), I’ll use this setup:\n"
                f"- Frontend: {spec['frontend']}\n"
                f"- Backend: {spec['backend']}\n"
                f"- Database: {spec['database']}\n\n"
                "You don’t have to worry about these names if you’re not technical.\n"
                "Now, please give this project a short name, for example:\n"
                '"my_product_site" or "team_dashboard".'
            )
        return "Tell me what style you like: minimal, bold, dark, playful…"

    if (
        any(x in msg_lower for x in ["fastapi", "node", "laravel", "spring", "go"])
        or any(x in msg_lower for x in ["react", "next", "vue", "svelte", "flutter"])
        or "sqlite" in msg_lower
        or "postgres" in msg_lower
        or "mysql" in msg_lower
        or "mongo" in msg_lower
    ) and "module_name" not in spec:
        t = msg_lower
        if "next" in t:
            spec["frontend"] = "nextjs"
        elif "react" in t:
            spec["frontend"] = "react"
        elif "vue" in t:
            spec["frontend"] = "vue"
        elif "flutter" in t:
            spec["frontend"] = "flutter"

        if "fastapi" in t:
            spec["backend"] = "fastapi"
        elif "node" in t:
            spec["backend"] = "node"
        elif "laravel" in t:
            spec["backend"] = "laravel"
        elif "spring" in t:
            spec["backend"] = "spring_boot"
        elif "go" in t:
            spec["backend"] = "go"

        if "postgres" in t:
            spec["database"] = "postgres"
        elif "mysql" in t:
            spec["database"] = "mysql"
        elif "mongo" in t:
            spec["database"] = "mongodb"
        elif "sqlite" in t:
            spec["database"] = "sqlite"

        return (
            "Understood, I’ve updated the technical stack based on your message.\n\n"
            "Now please give this project a short name. "
            "I’ll also use it for the main module and folders."
        )

    if "module_name" not in spec:
        if msg:
            spec["module_name"] = _slug_from_goal(msg)
        else:
            spec["module_name"] = _slug_from_goal(spec.get("goal", "app"))

        session["stage"] = "ready_to_build"
        if msg_lower in {"build", "go", "start", "generate", "yes"}:
            return _start_build(session)
        if msg:
            _update_spec_from_freeform(spec, msg, msg_lower)
        summary = _spec_summary(spec)
        _parse_goal_block_into_spec(spec, msg)
        _update_spec_from_freeform(spec, msg, msg_lower)
        return (
            summary + "\n\n"
            'If this looks good, you can simply reply with "build" '
            '(or "yes", "go", "start").\n'
            "If something is wrong or missing, just tell me in your own words "
            "and I’ll adjust it."
        )
        # - "switch backend to node"
        # - "add payments"
        # - "make it darker"
        changed = False

        if msg:
            if _apply_spec_edits_from_text(spec, msg_lower):
                changed = True
            if _update_spec_from_freeform(spec, msg, msg_lower):
                changed = True

        summary = _spec_summary(spec)
        if changed:
            return (
                summary + "\n\n"
                "I’ve updated the spec based on your message.\n\n"
                'If this looks good, reply with "build" to start generation.'
                "Otherwise, tell me any other changes you want."
            )

        return (
            summary + "\n\n"
            "You can now:\n"
            '- Type "build" to start generation, or\n'
            "- Tell me any changes, for example: "
            '"make it darker", "add payments", or "add an admin page".'
        )


def _maybe_enqueue_repo_summary(session: Dict[str, Any]) -> None:
    spec: Dict[str, Any] = session.setdefault("spec", {})
    jobs: Dict[str, Any] = session.setdefault("jobs", {})

    # Only do it if user enabled it via spec flag (so no surprises)
    # Set spec["use_repo_summary"]=True from UI/assistant message later.
    if not spec.get("use_repo_summary"):
        return

    if spec.get("repo_summary"):
        return

    if jobs.get("repo_summary"):
        return

    repo_root = spec.get("repo_root") or "."
    payload = {
        "root": repo_root,
        "focus_dirs": spec.get("repo_focus_dirs") or ["src", "services", "agents", "tests"],
        "include_snippets": bool(spec.get("repo_include_snippets", False)),
        "snippet_max_files": int(spec.get("repo_snippet_max_files", 15) or 15),
        "snippet_max_bytes_per_file": int(spec.get("repo_snippet_max_bytes_per_file", 300) or 300),
        "snippet_max_total_bytes": int(spec.get("repo_snippet_max_total_bytes", 4000) or 4000),
        "snippet_redact": True,
    }
    jid = q.enqueue(task="repo_summary", payload=payload, priority=0)
    jobs["repo_summary"] = jid


def _maybe_attach_repo_summary_result(session: Dict[str, Any]) -> None:
    spec: Dict[str, Any] = session.setdefault("spec", {})
    jobs: Dict[str, Any] = session.setdefault("jobs", {})

    jid = jobs.get("repo_summary")
    if not jid or spec.get("repo_summary"):
        return

    job = _get_job(int(jid))
    if not job:
        return

    if (job.get("status") or "").lower() != "done":
        return

    res = _job_result_json(job)
    if isinstance(res, dict):
        spec["repo_summary"] = res


def _derive_plan_tier(mode: str, security: str) -> str:
    """
    Map (assistant_mode, security_posture) -> plan_tier.
    Internal canonical values only:
      - "starter" | "pro" | "enterprise"
    """
    m = (mode or "basic").lower()
    s = (security or "standard").lower()

    if m == "architect" and s == "hardened":
        return "enterprise"
    if m in {"pro", "architect"}:
        return "pro"
    return "starter"


def handle(payload: Mapping[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {})
    msg = str(data.get("message", "")).strip()
    session_id = str(data.get("session_id") or "velu_default").strip() or "velu_default"
    use_repo_summary = bool(data.get("use_repo_summary"))
    repo_root = str(data.get("repo_root") or ".").strip() or "."
    repo_focus_dirs = data.get("repo_focus_dirs") or data.get("focus_dirs") or None

    backend = str(data.get("backend") or DEFAULT_BACKEND).strip().lower()
    if backend not in BACKENDS:
        backend = "rules"

    reset_flag = bool(data.get("reset") or data.get("reset_session"))

    normalized = msg.lower().strip()
    if normalized in {
        "reset",
        "start over",
        "new",
        "new project",
        "new app",
        "new website",
        "clear",
    }:
        reset_flag = True
        msg = ""

    if reset_flag:
        session = _new_session(session_id)
        session["backend"] = backend
        assistant_msg = _next_question(session, "")
        _add_history(session, "assistant", assistant_msg)
        spec = session.setdefault("spec", {})
        _normalize_tier_fields(spec)
        _save_session(session)

        return {
            "session_id": session_id,
            "backend": backend,
            "stage": session.get("stage"),
            "spec": spec,
            "message": assistant_msg,
            "jobs": session.get("jobs", {}),
            "history_tail": session.get("history", [])[-HISTORY_TAIL:],
            "project_summary": _project_summary_or_empty(session),
        }

    session = _load_session(session_id)
    spec = session.setdefault("spec", {})
    spec["use_repo_summary"] = use_repo_summary
    spec["repo_root"] = repo_root
    if repo_focus_dirs is not None:
        spec["repo_focus_dirs"] = repo_focus_dirs

    session["backend"] = backend

    if not msg:
        assistant_msg = _next_question(session, "")
        _add_history(session, "assistant", assistant_msg)
        spec = session.setdefault("spec", {})
        _normalize_tier_fields(spec)
        _save_session(session)

        return {
            "session_id": session_id,
            "backend": backend,
            "stage": session.get("stage"),
            "spec": spec,
            "message": assistant_msg,
            "jobs": session.get("jobs", {}),
            "history_tail": session.get("history", [])[-HISTORY_TAIL:],
            "project_summary": _project_summary_or_empty(session),
        }

    _add_history(session, "user", msg)

    if backend == "rules":
        assistant_msg = _run_rules_backend(session, msg)
    elif backend == "local_llm":
        assistant_msg = _call_local_llm(session, msg)
    else:
        assistant_msg = _call_remote_llm(session, msg)

    _add_history(session, "assistant", assistant_msg)
    spec = session.setdefault("spec", {})
    _normalize_tier_fields(spec)
    _save_session(session)

    return {
        "session_id": session_id,
        "backend": backend,
        "stage": session.get("stage"),
        "spec": spec,
        "message": assistant_msg,
        "jobs": session.get("jobs", {}),
        "history_tail": session.get("history", [])[-HISTORY_TAIL:],
        "project_summary": _project_summary_or_empty(session),
    }
