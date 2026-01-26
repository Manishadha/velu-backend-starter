# configs/language_catalog.py
from __future__ import annotations
from typing import Dict, List, TypedDict


class Language(TypedDict):
    code: str  # BCP-47 / ISO code
    name_en: str  # Name in English
    name_native: str  # Native display name
    region: str | None  # Optional (helps UI grouping)


# 🌍 60 Most Spoken + Business Critical Languages
ALL_LANGUAGES: List[Language] = [
    {"code": "en", "name_en": "English", "name_native": "English", "region": "Global"},
    {"code": "es", "name_en": "Spanish", "name_native": "Español", "region": "Global"},
    {"code": "fr", "name_en": "French", "name_native": "Français", "region": "Europe"},
    {"code": "de", "name_en": "German", "name_native": "Deutsch", "region": "Europe"},
    {"code": "pt", "name_en": "Portuguese", "name_native": "Português", "region": "Global"},
    {
        "code": "pt-BR",
        "name_en": "Portuguese (Brazil)",
        "name_native": "Português (Brasil)",
        "region": "South America",
    },
    {"code": "it", "name_en": "Italian", "name_native": "Italiano", "region": "Europe"},
    {"code": "nl", "name_en": "Dutch", "name_native": "Nederlands", "region": "Europe"},
    {"code": "pl", "name_en": "Polish", "name_native": "Polski", "region": "Europe"},
    {"code": "tr", "name_en": "Turkish", "name_native": "Türkçe", "region": "Middle East"},
    {"code": "ru", "name_en": "Russian", "name_native": "Русский", "region": "Europe/Asia"},
    {"code": "uk", "name_en": "Ukrainian", "name_native": "Українська", "region": "Europe"},
    {"code": "ro", "name_en": "Romanian", "name_native": "Română", "region": "Europe"},
    {"code": "hu", "name_en": "Hungarian", "name_native": "Magyar", "region": "Europe"},
    {"code": "cs", "name_en": "Czech", "name_native": "Čeština", "region": "Europe"},
    {"code": "sv", "name_en": "Swedish", "name_native": "Svenska", "region": "Europe"},
    {"code": "no", "name_en": "Norwegian", "name_native": "Norsk", "region": "Europe"},
    {"code": "da", "name_en": "Danish", "name_native": "Dansk", "region": "Europe"},
    {"code": "fi", "name_en": "Finnish", "name_native": "Suomi", "region": "Europe"},
    {"code": "el", "name_en": "Greek", "name_native": "Ελληνικά", "region": "Europe"},
    # Middle East / Africa
    {"code": "ar", "name_en": "Arabic", "name_native": "العربية", "region": "MENA"},
    {"code": "fa", "name_en": "Persian", "name_native": "فارسی", "region": "Iran"},
    {"code": "ku", "name_en": "Kurdish", "name_native": "Kurdî", "region": "MENA"},
    {"code": "am", "name_en": "Amharic", "name_native": "አማርኛ", "region": "Africa"},
    {"code": "ha", "name_en": "Hausa", "name_native": "Hausa", "region": "Africa"},
    {"code": "ig", "name_en": "Igbo", "name_native": "Igbo", "region": "Africa"},
    {"code": "sw", "name_en": "Swahili", "name_native": "Kiswahili", "region": "Africa"},
    {"code": "yo", "name_en": "Yoruba", "name_native": "Yorùbá", "region": "Africa"},
    {"code": "zu", "name_en": "Zulu", "name_native": "isiZulu", "region": "Africa"},
    # Asia
    {"code": "zh", "name_en": "Chinese (Simplified)", "name_native": "简体中文", "region": "China"},
    {
        "code": "zh-TW",
        "name_en": "Chinese (Traditional)",
        "name_native": "繁體中文",
        "region": "Taiwan",
    },
    {"code": "ja", "name_en": "Japanese", "name_native": "日本語", "region": "Japan"},
    {"code": "ko", "name_en": "Korean", "name_native": "한국어", "region": "South Korea"},
    {"code": "hi", "name_en": "Hindi", "name_native": "हिन्दी", "region": "India"},
    {"code": "bn", "name_en": "Bengali", "name_native": "বাংলা", "region": "Bangladesh/India"},
    {"code": "ta", "name_en": "Tamil", "name_native": "தமிழ்", "region": "India"},
    {"code": "ml", "name_en": "Malayalam", "name_native": "മലയാളം", "region": "India"},
    {"code": "te", "name_en": "Telugu", "name_native": "తెలుగు", "region": "India"},
    {"code": "ur", "name_en": "Urdu", "name_native": "اردو", "region": "Pakistan/India"},
    {"code": "pa", "name_en": "Punjabi", "name_native": "ਪੰਜਾਬੀ", "region": "India/Pakistan"},
    {"code": "si", "name_en": "Sinhala", "name_native": "සිංහල", "region": "Sri Lanka"},
    {"code": "th", "name_en": "Thai", "name_native": "ไทย", "region": "Thailand"},
    {"code": "vi", "name_en": "Vietnamese", "name_native": "Tiếng Việt", "region": "Vietnam"},
    {
        "code": "id",
        "name_en": "Indonesian",
        "name_native": "Bahasa Indonesia",
        "region": "Indonesia",
    },
    {"code": "tl", "name_en": "Tagalog", "name_native": "Tagalog", "region": "Philippines"},
    {"code": "my", "name_en": "Burmese", "name_native": "မြန်မာစာ", "region": "Myanmar"},
    {"code": "km", "name_en": "Khmer", "name_native": "ភាសាខ្មែរ", "region": "Cambodia"},
    {"code": "lo", "name_en": "Lao", "name_native": "ລາວ", "region": "Laos"},
    {"code": "mn", "name_en": "Mongolian", "name_native": "Монгол", "region": "Mongolia"},
    # Americas
    {"code": "qu", "name_en": "Quechua", "name_native": "Kichwa", "region": "Peru/Bolivia"},
    {"code": "gn", "name_en": "Guarani", "name_native": "Avañe'ẽ", "region": "Paraguay"},
    {"code": "ay", "name_en": "Aymara", "name_native": "Aymar", "region": "Bolivia"},
    {"code": "ht", "name_en": "Haitian Creole", "name_native": "Kreyòl Ayisyen", "region": "Haiti"},
]


LANG_BY_CODE: Dict[str, Language] = {l["code"]: l for l in ALL_LANGUAGES}  # noqa: E741


def get_language(code: str) -> Language | None:
    return LANG_BY_CODE.get(code)


def list_codes() -> List[str]:
    return list(LANG_BY_CODE.keys())
