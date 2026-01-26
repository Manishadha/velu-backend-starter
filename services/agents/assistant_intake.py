from __future__ import annotations

from typing import Any, Dict, List

from services.agents.language_detector import detect_language
from services.agents import content_generator
from services.app_server.schemas.intake import Company, Intake, Product
from services.app_server.schemas.blueprint_factory import blueprint_from_intake
from services.agents import intake_rules  # noqa: F401


def _build_company(data: Dict[str, Any]) -> Company:
    name_raw = data.get("name") or "Product"
    name = str(name_raw).strip() or "Product"
    industry = data.get("industry")
    region = data.get("region")
    contact_email = data.get("contact_email")
    return Company(
        name=name,
        industry=industry,
        region=region,
        contact_email=contact_email,  # type: ignore[arg-type]
    )


def _ensure_str_list(value: Any) -> List[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: List[str] = []
    for v in value:
        s = str(v).strip()
        if s:
            out.append(s)
    return out


def _build_product(
    data: Dict[str, Any], detected_lang: str | None, idea_text: str | None
) -> Product:
    # Raw values from payload (if any)
    type_raw = data.get("type")
    goal_raw = data.get("goal")
    raw_channels = data.get("channels")

    # Heuristic defaults from the idea
    inferred_type, inferred_goal = intake_rules.infer_type_and_goal(idea_text or "")
    inferred_channels = intake_rules.infer_channels(idea_text or "", fallback=["web"])  # noqa: F841

    # --- TYPE ---
    type_str = str(type_raw or "").strip().lower()
    if type_str not in {
        "website",
        "saas",
        "mobile_app",
        "ecommerce",
        "marketplace",
        "portal",
        "docs",
    }:
        type_str = inferred_type

    # --- GOAL ---
    goal_str = str(goal_raw or "").strip().lower()
    if goal_str not in {
        "lead_gen",
        "self_service",
        "transactions",
        "community",
        "internal_tool",
    }:
        goal_str = inferred_goal

    # --- CHANNELS ---
    explicit_channels: list[str] = []
    if isinstance(raw_channels, (list, tuple)):
        for ch in raw_channels:
            s = str(ch or "").strip().lower()
            if s:
                explicit_channels.append(s)
    channels = intake_rules.infer_channels(idea_text or "", fallback=explicit_channels or ["web"])

    # --- LOCALES ---
    audiences = _ensure_str_list(data.get("audiences") or [])
    raw_locales = _ensure_str_list(data.get("locales"))
    if raw_locales:
        locales = raw_locales
    else:
        locales = [detected_lang or "en"]

    brand_assets = data.get("brand_assets")

    return Product(
        type=type_str,  # type: ignore[arg-type]
        goal=goal_str,  # type: ignore[arg-type]
        audiences=audiences,
        channels=channels,  # type: ignore[list-item]
        locales=locales,
        brand_assets=brand_assets,
    )


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    idea = str(payload.get("idea") or "").strip()
    language = detect_language(idea) if idea else "en"

    company_data = payload.get("company") or {}
    product_data = payload.get("product") or {}

    company = _build_company(company_data)
    #  pass idea into _build_product
    product = _build_product(product_data, language, idea)

    intake = Intake(
        company=company,
        product=product,
        user_language=language,
        original_text_language=language,
    )

    blueprint = blueprint_from_intake(intake)

    cg_result = content_generator.handle({"blueprint": blueprint})
    locales = cg_result.get("locales") or []
    messages = cg_result.get("messages") or cg_result.get("content") or {}
    summary = cg_result.get("summary") or {}

    # 🔧 Post-process blueprint dict based on the original idea (db/plugins/tier)
    bp_dict = blueprint.model_dump()
    bp_dict = intake_rules.enrich_blueprint_dict(bp_dict, idea)

    return {
        "ok": True,
        "agent": "assistant_intake",
        "language": language,
        "intake": intake.model_dump(),
        "blueprint": bp_dict,
        "i18n": {
            "locales": locales,
            "messages": messages,
            "summary": summary,
        },
    }
