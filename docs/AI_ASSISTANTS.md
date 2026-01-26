# AI Assistants in Velu

This document describes the AI helpers that Velu exposes as internal "agents".
They are wired to work with either the rules backend or a real LLM backend
configured via `docs/AI_BACKENDS.md`.

The main assistants are:

- AI Architect
- Code Refiner
- Test Fix Assistant
- Debug Pipeline
- DB Schema Optimizer
- Content Generator
- Chatbot Embed

Each assistant follows the same pattern: `handle(payload: dict) -> dict` (or
a simple function returning a dict) and is designed so that tests are green
without external API keys.

## 1. AI Architect

Module: `services.agents.ai_architect`

Purpose: turn a short product description into a high-level architecture plan.

Typical fields in the result:

- `ok`: bool
- `plan`: list of steps or components
- `notes`: optional text summary

Example usage:

```python
from services.agents import ai_architect

payload = {
    "description": "Team dashboard for tracking tasks, incidents and on-call status.",
    "constraints": {
        "frontend": "nextjs",
        "backend": "fastapi",
    },
}

result = ai_architect.handle(payload)
assert result["ok"] is True
plan = result.get("plan") or []


The architect is intended to be called early in a pipeline, before more
concrete scaffolding.

2. Code Refiner

Module: services.agents.code_refiner

Purpose: take a single file and a set of review comments and produce a refined
version of that file. Works even when no remote LLM is configured by applying
simple local transformations.

Example:

from services.agents import code_refiner

payload = {
    "path": "services/app_server/main.py",
    "content": "print('hello')\n",
    "comments": [
        "Please avoid bare print and use logging instead.",
    ],
}

result = code_refiner.handle(payload)
assert result["ok"] is True
new_content = result.get("content", "")


The refiner tries to be conservative so that tests remain green.

3. Test Fix Assistant

Module: services.agents.test_fix_assistant

Purpose: take failing test output and suggest candidate code edits to fix the
failures. The edits are represented as patch-like structures.

Example:

from services.agents import test_fix_assistant

payload = {
    "failing_tests": ["tests/test_math_mod.py::test_add"],
    "stderr": "E   AssertionError: expected 4, got 5",
    "repo_summary": "Simple math module with add/sub/mul.",
}

result = test_fix_assistant.handle(payload)
assert result["ok"] is True
patches = result.get("patches") or []


The patches can then be applied by a higher-level pipeline step or an editor.

4. Debug Pipeline Assistant

Module: services.agents.debug_pipeline

Purpose: reason about a whole pipeline of steps and diagnostics. It can consume
a compact summary (like the output of services.console.debug_runner) and
produce a human-readable analysis.

Example:

from services.agents import debug_pipeline

payload = {
    "tests": {
        "total": 139,
        "failed": [],
        "skipped": ["tests/test_slow_integration.py::test_big_case"],
    },
    "last_run_seconds": 8.0,
}

result = debug_pipeline.handle(payload)
assert result["ok"] is True
report = result.get("report", "")


This is useful when building introspection features for Velu itself.

5. DB Schema Optimizer

Module: services.agents.db_schema_optimizer

Purpose: inspect a simple logical schema (tables, columns, indexes) and return
a set of improvement suggestions.

Example:

from services.agents import db_schema_optimizer

schema = {
    "tables": [
        {
            "name": "events",
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "user_id", "type": "uuid"},
                {"name": "created_at", "type": "timestamptz"},
            ],
            "indexes": [],
        }
    ]
}

result = db_schema_optimizer.handle({"schema": schema})
assert result["ok"] is True
suggestions = result.get("suggestions") or []


The optimizer focuses on simple, deterministic rules so it does not require an
external model to be useful.

6. Content Generator

Module: services.agents.content_generator

Purpose: generate human-readable copy for pages, emails, or UI components,
based on a small prompt and optional locale.

Example:

from services.agents import content_generator

payload = {
    "kind": "landing_page",
    "locale": "en",
    "product_name": "Velu",
    "description": "An AI-powered app generator for developers.",
}

result = content_generator.handle(payload)
assert result["ok"] is True
sections = result.get("sections") or []


When a remote LLM is configured, the generator can delegate more of the
creative work. Without it, it still produces deterministic, testable text.

7. Chatbot Embed

Module: services.agents.chatbot_embed

Purpose: generate frontend files to embed a small chat widget that talks to the
Velu AI chat endpoint (for example /v1/ai/chat).

Files produced:

web/components/VeluChatWidget.tsx

web/chatbot.config.json

Example:

from services.agents import chatbot_embed

payload = {
    "blueprint": {
        "name": "Team Dashboard",
        "kind": "dashboard",
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "fr"],
        },
    }
}

result = chatbot_embed.handle(payload)
assert result["ok"] is True
files = result.get("files") or []


The widget uses a simple JSON API contract so it can work against either a
rules-based backend or a remote LLM backend depending on configuration.

8. Relation to AI backends

All of these assistants are designed to run in a "rules-only" mode by default
so that:

pytest does not require network access

test results are deterministic

When environment variables described in docs/AI_BACKENDS.md are set, these
agents can route calls through the configured remote LLM provider while
preserving safe fallbacks.


---

## 2️⃣ Add a tiny doc–example test

Create `tests/test_ai_assistants_docs_examples.py` with this content:

```python
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

    ref = code_refiner.handle(
        {"path": "foo.py", "content": "print('x')\n", "comments": []}
    )
    assert ref["ok"] is True
    assert isinstance(ref.get("content", ""), str)

    fix = test_fix_assistant.handle(
        {"failing_tests": ["tests/test_dummy.py::test_x"], "stderr": "AssertionError"}
    )
    assert fix["ok"] is True

    cg = content_generator.handle(
        {"kind": "landing_page", "locale": "en", "product_name": "Velu"}
    )
    assert cg["ok"] is True

    cb = chatbot_embed.handle({"blueprint": {"name": "Demo", "kind": "web_app"}})
    assert cb["ok"] is True
    files = cb.get("files") or []
    paths = {f["path"] for f in files}
    assert "web/components/VeluChatWidget.tsx" in paths
    assert "web/chatbot.config.json" in paths


This just ensures the examples in the doc don’t silently drift away from the actual code behaviour.
