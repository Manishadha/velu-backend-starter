from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from services.agents import content_generator, language_detector


class LocalesResponse(BaseModel):
    locales: List[str]


class MessagesResponse(BaseModel):
    locale: str
    locales: List[str]
    messages: Dict[str, Any]
    summary: Dict[str, Any] | None = None


class TranslateRequest(BaseModel):
    text: str
    target_locale: str
    source_locale: str | None = None


class TranslateResponse(BaseModel):
    text: str
    translated_text: str
    source_locale: str
    target_locale: str
    backend: str = "stub"


router = APIRouter(prefix="/v1/i18n", tags=["i18n"])

DEFAULT_LOCALES = ["en", "fr", "nl", "de", "ar", "ta"]


def _parse_accept_language_header(header_value: str | None) -> List[Tuple[str, float]]:
    if not header_value:
        return []
    parts = [p.strip() for p in header_value.split(",") if p.strip()]
    out: List[Tuple[str, float]] = []
    for part in parts:
        if ";" in part:
            lang, _, rest = part.partition(";")
            lang = lang.strip()
            q = 1.0
            if rest.startswith("q="):
                try:
                    q = float(rest[2:])
                except ValueError:
                    q = 1.0
        else:
            lang = part
            q = 1.0
        if not lang:
            continue
        out.append((lang.lower(), q))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def _pick_best_locale(
    requested: Sequence[Tuple[str, float]],
    supported: Sequence[str],
    default_locale: str = "en",
) -> str:
    supported_set = {s.lower() for s in supported}
    for lang, _q in requested:
        if lang in supported_set:
            return lang
        if "-" in lang:
            base = lang.split("-", 1)[0]
            if base in supported_set:
                return base
    return default_locale


def _content_to_messages(content: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for code, data in content.items():
        locale = str(code)
        sections = data.get("sections") or []
        title = data.get("title") or ""
        tagline = data.get("tagline") or ""

        hero_section = None
        for s in sections:
            if s.get("id") == "hero":
                hero_section = s
                break

        hero_title = title
        hero_tagline = tagline
        hero_cta = None

        if hero_section:
            hero_title = hero_section.get("heading") or hero_title
            hero_tagline = hero_section.get("body") or hero_tagline
            hero_cta = hero_section.get("primary_cta")

        out[locale] = {
            "locale": locale,
            "hero": {
                "title": hero_title,
                "tagline": hero_tagline,
                "primary_cta": hero_cta,
            },
            "sections": sections,
        }
    return out


def _stub_translate(text: str, source_locale: str, target_locale: str) -> str:
    if not text.strip():
        return ""
    if source_locale.lower() == target_locale.lower():
        return text
    prefix = f"[{target_locale}] "
    return prefix + text


@router.get("/locales", response_model=LocalesResponse)
async def get_locales() -> LocalesResponse:
    return LocalesResponse(locales=list(DEFAULT_LOCALES))


@router.get("/messages", response_model=MessagesResponse)
async def get_messages(
    locale: str | None = Query(default=None),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> MessagesResponse:
    if locale:
        selected = locale.strip().lower() or "en"
    else:
        requested = _parse_accept_language_header(accept_language)
        selected = _pick_best_locale(requested, DEFAULT_LOCALES, default_locale="en")

    payload: Dict[str, Any] = {
        "product": {
            "name": "Velu application",
            "locales": list(DEFAULT_LOCALES),
        }
    }
    base = content_generator.handle(payload)
    locales = base.get("locales") or list(DEFAULT_LOCALES)
    content = base.get("content") or {}
    summary = base.get("summary") or {}

    messages = _content_to_messages(content)

    if selected not in {l.lower() for l in locales}:  # noqa: E741
        selected = "en"

    return MessagesResponse(
        locale=selected,
        locales=list(locales),
        messages=messages,
        summary=summary,
    )


@router.post("/messages")
async def post_messages(body: Dict[str, Any]) -> Dict[str, Any]:
    base = content_generator.handle(body)
    locales = base.get("locales") or []
    content = base.get("content") or {}
    summary = base.get("summary") or {}

    messages = _content_to_messages(content)

    if locales:
        selected = str(locales[0])
    else:
        selected = "en"

    return {
        "ok": True,
        "agent": "content_generator",
        "locale": selected,
        "locales": locales,
        "content": content,
        "summary": summary,
        "messages": messages,
    }


@router.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest) -> TranslateResponse:
    text = req.text or ""
    src = (req.source_locale or "").strip()
    if not src:
        detected: str | None
        try:
            detected = language_detector.detect_language(text)
        except Exception:
            detected = None
        src = detected or "und"
    tgt = (req.target_locale or "en").strip() or "en"
    translated = _stub_translate(text, src, tgt)
    return TranslateResponse(
        text=text,
        translated_text=translated,
        source_locale=src,
        target_locale=tgt,
        backend="stub",
    )
