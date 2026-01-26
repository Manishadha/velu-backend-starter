from __future__ import annotations

from typing import Final


LATIN_FRENCH_HINTS: Final[tuple[str, ...]] = (
    "bonjour",
    "monde",
    "équipe",
    "equipe",
    "tableau de bord",
    "en français",
    "français",
)

LATIN_DUTCH_HINTS: Final[tuple[str, ...]] = (
    "hallo",
    "allemaal",
    "goedemorgen",
    "goedenavond",
)

LATIN_GERMAN_HINTS: Final[tuple[str, ...]] = (
    "guten tag",
    "guten morgen",
    "guten abend",
    "tschüss",
    "auf wiedersehen",
)

LATIN_SPANISH_HINTS: Final[tuple[str, ...]] = (
    "hola",
    "buenos días",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "¿qué tal",
    "que tal",
    "qué tal",
    "quiero",
    "aplicación",
    "aplicacion",
    "negocio",
)


def detect_language(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "en"

    low = t.lower()

    for ch in low:
        code = ord(ch)
        if 0x0600 <= code <= 0x06FF:
            return "ar"
        if 0x0B80 <= code <= 0x0BFF:
            return "ta"
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x3040 <= code <= 0x30FF:
            return "zh"

    if any(h in low for h in LATIN_FRENCH_HINTS):
        return "fr"
    if any(h in low for h in LATIN_SPANISH_HINTS):
        return "es"
    if any(h in low for h in LATIN_DUTCH_HINTS):
        return "nl"
    if any(h in low for h in LATIN_GERMAN_HINTS):
        return "de"

    if "¡hola" in low:
        return "es"

    return "en"
