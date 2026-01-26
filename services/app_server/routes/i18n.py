# services/app_server/routes/i18n.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.agents import language_detector

router = APIRouter()

_ALL_LOCALES = ["en", "fr", "nl", "de", "ar", "ta"]


class ProductIn(BaseModel):
    name: str = "Velu application"
    locales: List[str] = Field(default_factory=lambda: ["en"])


class MessagesRequest(BaseModel):
    product: ProductIn


class TranslateRequest(BaseModel):
    text: str
    target_locale: str
    source_locale: Optional[str] = None


def _primary_cta_for_locale(locale: str) -> str:
    mapping = {
        "en": "Get started",
        "fr": "Commencer",
        "nl": "Aan de slag",
        "de": "Loslegen",
        "ar": "ابدأ الآن",
        "ta": "தொடங்குங்கள்",
    }
    return mapping.get(locale, "Get started")


def _build_messages(name: str, locales: List[str]) -> Dict[str, Any]:
    messages: Dict[str, Any] = {}
    for loc in locales:
        cta = _primary_cta_for_locale(loc)
        hero_title = f"{name} · A modern product experience"
        hero_tagline = "Responsive, secure, and ready for production."
        messages[loc] = {
            "locale": loc,
            "hero": {
                "title": hero_title,
                "tagline": hero_tagline,
                "primary_cta": cta,
            },
            "sections": [
                {
                    "id": "hero",
                    "heading": hero_title,
                    "body": hero_tagline,
                    "primary_cta": cta,
                },
                {
                    "id": "features",
                    "heading": "Key capabilities",
                    "body": (
                        f"{name} helps you ship a web_app with "
                        "sensible defaults and production-ready patterns."
                    ),
                },
                {
                    "id": "getting_started",
                    "heading": "Getting started",
                    "body": "Clone the repo, configure your environment, "
                    "and run the provided dev commands.",
                },
            ],
        }
    return messages


@router.get("/v1/i18n/locales")
def get_locales() -> Dict[str, Any]:
    """
    Simple list of supported locales for the Velu demo.
    """
    return {"locales": _ALL_LOCALES}


@router.get("/v1/i18n/messages")
def get_messages(locale: str = "en") -> Dict[str, Any]:
    """
    Demo messages for the Velu application.
    Mirrors the shape of the generated demo endpoints.
    """
    messages = _build_messages("Velu application", _ALL_LOCALES)
    return {
        "locale": locale,
        "locales": _ALL_LOCALES,
        "messages": messages,
        "summary": {
            "locales": _ALL_LOCALES,
            "kind": "web_app",
            "name": "Velu application",
        },
    }


@router.post("/v1/i18n/messages")
def post_messages(body: MessagesRequest) -> Dict[str, Any]:
    """
    Generate simple marketing copy for a given product & locales.
    Uses a static template; no external API calls.
    """
    name = body.product.name or "Product"
    locales = body.product.locales or ["en"]
    messages = _build_messages(name, locales)
    primary_locale = locales[0] if locales else "en"

    # "content" is a slightly different view used in earlier demos.
    content: Dict[str, Any] = {}
    for loc in locales:
        hero = messages[loc]["hero"]
        sections = messages[loc]["sections"]
        content[loc] = {
            "locale": loc,
            "title": hero["title"],
            "tagline": hero["tagline"],
            "sections": sections,
        }

    return {
        "ok": True,
        "agent": "content_generator",
        "locale": primary_locale,
        "locales": locales,
        "content": content,
        "summary": {
            "locales": locales,
            "kind": "web_app",
            "name": name,
        },
        "messages": messages,
    }


@router.post("/v1/i18n/translate")
def translate(body: TranslateRequest) -> Dict[str, Any]:
    """
    Very simple demo translator:
    - Detects source language if not provided (via language_detector.handle).
    - Returns text prefixed with [target_locale], like the old stub.
    """
    source = body.source_locale
    if not source:
        try:
            det = language_detector.handle({"text": body.text})
            source = str(det.get("language") or "en")
        except Exception:
            source = "en"

    return {
        "text": body.text,
        "translated_text": f"[{body.target_locale}] {body.text}",
        "source_locale": source,
        "target_locale": body.target_locale,
        "backend": "stub",
    }
