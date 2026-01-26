from __future__ import annotations

from typing import Any, Dict, List

from .blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintBrand,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLayout,
    BlueprintLocalization,
)
from .intake import Intake


def _slug(value: str) -> str:
    s = (value or "").strip().lower()
    if not s:
        return "product"
    buf: List[str] = []
    last_us = False
    for ch in s:
        if ch.isalnum():
            buf.append(ch)
            last_us = False
        else:
            if not last_us:
                buf.append("_")
                last_us = True
    out = "".join(buf).strip("_")
    return out or "product"


def _normalize_kind(raw: str | None) -> str:
    allowed = {
        "website",
        "web_app",
        "mobile_app",
        "dashboard",
        "api_only",
        "cli",
        "service",
    }
    v = (raw or "").strip().lower()
    if v in allowed:
        return v

    if v in {
        "saas",
        "portal",
        "docs",
        "ecommerce",
        "marketplace",
        "app",
        "webapp",
        "web application",
    }:
        return "web_app"
    if v in {"landing", "landing_page", "marketing_site"}:
        return "website"
    if v in {"mobile", "mobile application"}:
        return "mobile_app"
    if v in {"admin", "admin_panel", "backoffice", "dashboard_app"}:
        return "dashboard"
    if v in {"api", "rest_api", "graphql_api", "backend"}:
        return "api_only"
    if v in {"cli_tool", "script", "utility"}:
        return "cli"
    if v in {"microservice", "worker", "service_app"}:
        return "service"

    return "web_app"


def _targets_from_channels(channels: List[str] | None, kind: str) -> List[str]:
    ch = {c.strip().lower() for c in (channels or []) if c}
    targets: List[str] = []

    if kind == "mobile_app":
        if "android" in ch or not ch:
            targets.append("android")
        if "ios" in ch or not ch:
            targets.append("ios")
    else:
        if "web" in ch or not ch:
            targets.append("web")
        if "android" in ch:
            targets.append("android")
        if "ios" in ch:
            targets.append("ios")
        if "desktop" in ch:
            targets.append("desktop")

    return targets or ["web"]


def _normalize_font(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in {"system", "serif", "mono"}:
        return s
    return "system"


def _normalize_hero_style(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if s in {"centered", "split", "image_right"}:
        return s
    return None


def blueprint_from_intake(intake: Intake) -> Blueprint:
    company = intake.company
    product = intake.product

    kind = _normalize_kind(product.type)
    targets = _targets_from_channels(product.channels, kind)

    raw_locales = list(product.locales or ["en"])
    clean_locales: List[str] = []
    for l in raw_locales:  # noqa: E741
        s = str(l).strip()
        if s:
            clean_locales.append(s)
    if not clean_locales:
        clean_locales = ["en"]

    default_lang = clean_locales[0]
    supported = clean_locales

    frontend = BlueprintFrontend(
        framework="nextjs",
        language="typescript",
        targets=targets,
    )
    backend = BlueprintBackend(
        framework="fastapi",
        language="python",
        style="rest",
    )
    database = BlueprintDatabase(
        engine="sqlite",
        mode="single_node",
    )
    localization = BlueprintLocalization(
        default_language=default_lang,
        supported_languages=supported,
    )

    brand = BlueprintBrand(
        name=product.name or company.name or "Product",
    )

    if kind == "website":
        hero_style = "split"
    elif kind == "mobile_app":
        hero_style = "image_right"
    else:
        hero_style = "centered"

    layout = BlueprintLayout(
        hero_style=hero_style,  # type: ignore[arg-type]
    )

    return Blueprint(
        id=_slug(company.name),
        name=company.name or "Product",
        kind=kind,  # type: ignore[arg-type]
        frontend=frontend,
        backend=backend,
        database=database,
        localization=localization,
        brand=brand,
        layout=layout,
    )


def blueprint_from_hospital_spec(spec: Dict[str, Any]) -> Blueprint:
    project = spec.get("project") or {}
    stack = spec.get("stack") or {}
    loc = spec.get("localization") or {}

    raw_kind = project.get("type") or "web_app"
    kind = _normalize_kind(str(raw_kind))

    f_stack = stack.get("frontend") or {}
    b_stack = stack.get("backend") or {}
    d_stack = stack.get("database") or {}

    f_framework_raw = str(f_stack.get("framework") or "nextjs")
    f_framework = f_framework_raw.strip() or "nextjs"
    f_language_raw = str(f_stack.get("language") or "typescript")
    f_language = f_language_raw.strip() or "typescript"

    fw = f_framework.lower()
    if kind == "mobile_app" or fw in {"react_native", "flutter"}:
        targets: List[str] = ["android", "ios"]
    elif fw in {"tauri", "electron"}:
        targets = ["desktop"]
    else:
        targets = ["web"]

    frontend = BlueprintFrontend(
        framework=f_framework,
        language=f_language,
        targets=targets,
    )

    raw_backend_framework = str(b_stack.get("framework") or "fastapi")
    raw_backend_language = str(b_stack.get("language") or "").lower()

    bf = raw_backend_framework.lower()
    if bf in {"fastapi", "django"}:
        b_language = "python"
    elif bf in {"express", "nestjs", "node"}:
        b_language = raw_backend_language or "node"
    else:
        b_language = raw_backend_language or "python"

    b_style = str(b_stack.get("style") or "rest").lower()
    if b_style not in {"rest", "graphql", "rpc"}:
        b_style = "rest"

    backend = BlueprintBackend(
        framework=raw_backend_framework,
        language=b_language,
        style=b_style,  # type: ignore[arg-type]
    )

    d_engine = str(d_stack.get("engine") or "sqlite")
    d_mode = str(d_stack.get("mode") or "single_node").lower()
    if d_mode not in {"single_node", "clustered"}:
        d_mode = "single_node"

    database = BlueprintDatabase(
        engine=d_engine,
        mode=d_mode,  # type: ignore[arg-type]
    )

    default_lang = str(loc.get("default_language") or "en")
    supported_raw = loc.get("supported_languages") or [default_lang]
    supported = [str(x) for x in supported_raw if x]

    localization = BlueprintLocalization(
        default_language=default_lang,
        supported_languages=supported,
    )

    brand_spec = project.get("brand") or {}
    font_value = _normalize_font(brand_spec.get("font"))
    brand = BlueprintBrand(
        name=str(brand_spec.get("name") or project.get("name") or "Product"),
        primary_color=str(brand_spec.get("primary_color") or "#2563eb"),
        secondary_color=str(brand_spec.get("secondary_color") or "#0f172a"),
        accent_color=str(brand_spec.get("accent_color") or "#f97316"),
        font=font_value,  # type: ignore[arg-type]
        logo_url=brand_spec.get("logo_url"),
    )

    layout_spec = project.get("layout") or {}
    hero_style_norm = _normalize_hero_style(layout_spec.get("hero_style"))
    layout_kwargs: Dict[str, Any] = {}
    if hero_style_norm:
        layout_kwargs["hero_style"] = hero_style_norm
    for key in ["show_testimonials", "show_pricing", "show_cta"]:
        v = layout_spec.get(key)
        if isinstance(v, bool):
            layout_kwargs[key] = v
    layout = BlueprintLayout(**layout_kwargs)

    bp_id = str(project.get("id") or _slug(str(project.get("name") or "product")))
    bp_name = str(project.get("name") or "Product")

    return Blueprint(
        id=bp_id,
        name=bp_name,
        kind=kind,  # type: ignore[arg-type]
        frontend=frontend,
        backend=backend,
        database=database,
        localization=localization,
        brand=brand,
        layout=layout,
    )
