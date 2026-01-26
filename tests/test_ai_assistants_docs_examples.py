from __future__ import annotations

from services.agents import (
    ai_architect,
    code_refiner,
    test_fix_assistant,
    content_generator,
    chatbot_embed,
)


def test_ai_assistants_docs_examples_smoke():
    arch = ai_architect.handle({"description": "Simple team dashboard"})
    assert arch["ok"] is True

    ref = code_refiner.handle({"path": "foo.py", "content": "print('x')\n", "comments": []})
    assert ref["ok"] is True
    assert isinstance(ref.get("content", ""), str)

    fix = test_fix_assistant.handle(
        {"failing_tests": ["tests/test_dummy.py::test_x"], "stderr": "AssertionError"}
    )
    assert fix["ok"] is True

    cg = content_generator.handle({"kind": "landing_page", "locale": "en", "product_name": "Velu"})
    assert cg["ok"] is True

    cb = chatbot_embed.handle({"blueprint": {"name": "Demo", "kind": "web_app"}})
    assert cb["ok"] is True
    files = cb.get("files") or []
    paths = {f["path"] for f in files}
    assert "web/components/VeluChatWidget.tsx" in paths
    assert "web/chatbot.config.json" in paths
