from __future__ import annotations

from typing import Any, Dict, List


def _norm_str(value: Any, default: str = "") -> str:
    s = str(value or "").strip()
    return s or default


def _extract_locales_from_blueprint(bp: Any) -> List[str] | None:
    if isinstance(bp, dict):
        loc = bp.get("localization") or {}
        if isinstance(loc, dict):
            supported = loc.get("supported_languages")
            default = loc.get("default_language")
            out: List[str] = []
            if isinstance(supported, (list, tuple)):
                out = [str(x) for x in supported if str(x).strip()]
            if not out and isinstance(default, str) and default.strip():
                out = [default.strip()]
            return out or None

    localization = getattr(bp, "localization", None)
    if localization is not None:
        supported = getattr(localization, "supported_languages", None)
        default = getattr(localization, "default_language", None)
        out: List[str] = []
        if isinstance(supported, (list, tuple)):
            out = [str(x) for x in supported if str(x).strip()]
        if not out and isinstance(default, str) and default.strip():
            out = [default.strip()]
        return out or None

    return None


def _extract_locales(payload: Dict[str, Any]) -> List[str]:
    bp = payload.get("blueprint")
    if bp is not None:
        from_bp = _extract_locales_from_blueprint(bp)
        if from_bp:
            return from_bp

    raw_locales = payload.get("locales")
    if isinstance(raw_locales, (list, tuple)) and raw_locales:
        return [str(x) for x in raw_locales if str(x).strip()]

    product = payload.get("product")
    if isinstance(product, dict):
        prod_locales = product.get("locales")
        if isinstance(prod_locales, (list, tuple)) and prod_locales:
            return [str(x) for x in prod_locales if str(x).strip()]

    return ["en"]


def _extract_name_and_kind(payload: Dict[str, Any]) -> tuple[str, str]:
    bp = payload.get("blueprint")
    if bp is not None:
        if isinstance(bp, dict):
            name = _norm_str(bp.get("name"), "Product")
            kind = _norm_str(bp.get("kind"), "web_app")
            return name, kind
        name = _norm_str(getattr(bp, "name", None), "Product")
        kind = _norm_str(getattr(bp, "kind", None), "web_app")
        return name, kind

    product = payload.get("product") or {}
    if isinstance(product, dict):
        name = _norm_str(product.get("name"), "Product")
    else:
        name = "Product"

    kind = "web_app"
    return name, kind


def _base_copy_for_kind(kind: str) -> Dict[str, str]:
    k = kind.lower()
    if k == "dashboard":
        return {
            "hero_title": "Operational visibility for your team",
            "hero_tagline": "Track metrics, alerts, and workflows in one realtime dashboard.",
            "cta": "Open dashboard",
        }
    if k == "api_only":
        return {
            "hero_title": "A clean, modern API",
            "hero_tagline": "Ship features faster with a predictable, well-documented API.",
            "cta": "View API docs",
        }
    if k == "mobile_app":
        return {
            "hero_title": "Your product in your pocket",
            "hero_tagline": "Stay connected to your data and workflows anywhere.",
            "cta": "Install the app",
        }
    if k == "website":
        return {
            "hero_title": "Tell your product story",
            "hero_tagline": "A modern marketing site to convert visitors into users.",
            "cta": "Explore features",
        }
    return {
        "hero_title": "A modern product experience",
        "hero_tagline": "Responsive, secure, and ready for production.",
        "cta": "Get started",
    }


def _localize_label(locale: str, label: str) -> str:
    code = locale.lower()
    if code.startswith("fr"):
        if label == "Get started":
            return "Commencer"
        if label == "Open dashboard":
            return "Ouvrir le tableau de bord"
        if label == "View API docs":
            return "Voir la documentation API"
        if label == "Install the app":
            return "Installer l’application"
        if label == "Explore features":
            return "Découvrir les fonctionnalités"
    if code.startswith("nl"):
        if label == "Get started":
            return "Aan de slag"
        if label == "Open dashboard":
            return "Dashboard openen"
        if label == "View API docs":
            return "API-documentatie bekijken"
        if label == "Install the app":
            return "De app installeren"
        if label == "Explore features":
            return "Functies bekijken"
    if code.startswith("de"):
        if label == "Get started":
            return "Loslegen"
        if label == "Open dashboard":
            return "Dashboard öffnen"
        if label == "View API docs":
            return "API-Dokumentation anzeigen"
        if label == "Install the app":
            return "App installieren"
        if label == "Explore features":
            return "Funktionen entdecken"
    if code.startswith("ar"):
        if label == "Get started":
            return "ابدأ الآن"
        if label == "Open dashboard":
            return "افتح لوحة المعلومات"
        if label == "View API docs":
            return "عرض توثيق واجهة البرمجة"
        if label == "Install the app":
            return "ثبّت التطبيق"
        if label == "Explore features":
            return "استكشف المزايا"
    if code.startswith("ta"):
        if label == "Get started":
            return "தொடங்குங்கள்"
        if label == "Open dashboard":
            return "டாஷ்போர்டை திறக்கவும்"
        if label == "View API docs":
            return "API ஆவணத்தை பார்க்கவும்"
        if label == "Install the app":
            return "செயலியை நிறுவவும்"
        if label == "Explore features":
            return "அம்சங்களை ஆராயவும்"
    return label


def _build_locale_payload(
    locale: str, name: str, kind: str, base: Dict[str, str]
) -> Dict[str, Any]:
    hero_title = f"{name} · {base['hero_title']}"
    hero_tagline = base["hero_tagline"]
    cta_label = _localize_label(locale, base["cta"])

    return {
        "locale": locale,
        "title": hero_title,
        "tagline": hero_tagline,
        "sections": [
            {
                "id": "hero",
                "heading": hero_title,
                "body": hero_tagline,
                "primary_cta": cta_label,
            },
            {
                "id": "features",
                "heading": "Key capabilities",
                "body": f"{name} helps you ship a {kind} with sensible defaults and production-ready patterns.",
            },
            {
                "id": "getting_started",
                "heading": "Getting started",
                "body": "Clone the repo, configure your environment, and run the provided dev commands.",
            },
        ],
    }


def _build_messages_from_content(content: Dict[str, Any]) -> Dict[str, Any]:
    messages: Dict[str, Any] = {}
    for locale, data in content.items():
        loc = str(locale).strip()
        if not loc:
            continue

        sections = data.get("sections") or []
        hero_section: Dict[str, Any] | None = None
        for s in sections:
            if isinstance(s, dict) and s.get("id") == "hero":
                hero_section = s
                break

        if hero_section is None:
            hero_title = data.get("title", "")
            hero_tagline = data.get("tagline", "")
            primary_cta = _localize_label(loc, "Get started")
        else:
            hero_title = str(hero_section.get("heading") or data.get("title") or "")
            hero_tagline = str(hero_section.get("body") or data.get("tagline") or "")
            primary_cta_raw = hero_section.get("primary_cta") or "Get started"
            primary_cta = _localize_label(loc, str(primary_cta_raw))

        messages[loc] = {
            "locale": loc,
            "hero": {
                "title": hero_title,
                "tagline": hero_tagline,
                "primary_cta": primary_cta,
            },
            "sections": sections,
        }

    return messages


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    locales = _extract_locales(payload)
    name, kind = _extract_name_and_kind(payload)
    base = _base_copy_for_kind(kind)

    content: Dict[str, Any] = {}
    for loc in locales:
        loc_str = str(loc).strip()
        if not loc_str:
            continue
        content[loc_str] = _build_locale_payload(loc_str, name, kind, base)

    messages = _build_messages_from_content(content)

    summary = {
        "locales": sorted(content.keys()),
        "kind": kind,
        "name": name,
    }

    return {
        "ok": True,
        "agent": "content_generator",
        "locales": sorted(content.keys()),
        "content": content,
        "summary": summary,
        "messages": messages,
    }
