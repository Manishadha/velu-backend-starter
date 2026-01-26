from services.agents.language_detector import detect_language  # type: ignore


def test_detect_language_empty_defaults_to_en() -> None:
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"


def test_detect_language_english_fallback() -> None:
    assert detect_language("This is a simple app description.") == "en"


def test_detect_language_french_keywords() -> None:
    assert detect_language("Bonjour, je veux une application pour mon entreprise.") == "fr"


def test_detect_language_spanish_keywords() -> None:
    assert detect_language("Hola, quiero una app para mi negocio.") == "es"


def test_detect_language_arabic_script() -> None:
    assert detect_language("مرحبا أريد تطبيق حساب فواتير") == "ar"


def test_detect_language_tamil_script() -> None:
    assert detect_language("வணக்கம், எனக்கு ஒரு மருத்துவ ஆப் வேண்டும்") == "ta"


def test_detect_language_chinese_script() -> None:
    assert detect_language("你好，我想要一个旅游预订应用") == "zh"
