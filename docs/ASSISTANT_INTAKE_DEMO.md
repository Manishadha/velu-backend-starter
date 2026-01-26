# Velu Assistant Intake Demo

This guide shows how to exercise the assistant intake flow:

- Detects language from the free-text idea
- Builds an `Intake` object with product + language info
- Builds a `Blueprint` with localization fields
- Generates i18n content for the product

The main endpoint is:

- `POST /v1/assistant/intake`

> All logic runs locally by default (no external LLM required).

---

## 1. Start the embedded API server

From the repo root:

```bash
source .venv/bin/activate
export PYTHONPATH=src:generated
uvicorn generated.services.api.app:app --reload --host 0.0.0.0 --port 8000

should see Uvicorn listening on http://0.0.0.0:8000.

2. Basic assistant intake call

Minimal example with explicit locales:

curl -X POST http://localhost:8000/v1/assistant/intake \
  -H "Content-Type: application/json" \
  -d '{
    "company": { "name": "Acme Travel" },
    "product": {
      "type": "saas",
      "goal": "internal_tool",
      "locales": ["en", "fr"]
    },
    "idea": "tableau de bord pour mon équipe"
  }' | jq .


Expected shape of the response (simplified):

{
  "ok": true,
  "language": "fr",
  "intake": {
    "product": {
      "locales": ["en", "fr"],
      ...
    },
    "user_language": "fr",
    "original_text_language": "fr",
    ...
  },
  "blueprint": {
    "localization": {
      "default_language": "en",
      "supported_languages": ["en", "fr"]
    },
    ...
  },
  "i18n": {
    "locales": ["en", "fr"],
    "messages": {
      "en": { ... },
      "fr": { ... }
    },
    "summary": { ... }
  }
}


Key points:

language: detected language from the idea ("fr" here).

intake.product.locales: exactly what you sent (["en", "fr"]).

blueprint.localization.supported_languages: aligned to the product locales.

i18n.messages: localized content for each supported language.

3. Let the assistant infer locales from the idea

You can omit product.locales and let the assistant infer the language and suggest locales:

curl -X POST http://localhost:8000/v1/assistant/intake \
  -H "Content-Type: application/json" \
  -d '{
    "company": { "name": "Acme Travel" },
    "product": {
      "type": "saas",
      "goal": "internal_tool"
    },
    "idea": "tableau de bord pour mon équipe en français"
  }' | jq .


Things to look for:

language should start with "fr".

intake.user_language should also start with "fr".

intake.product.locales should include "fr" (e.g. ["fr"] or ["fr", "en"] depending on the logic).

blueprint.localization.supported_languages should match the updated locales.

i18n.locales and i18n.messages should contain the same set of locale codes.

4. Relationship to other APIs

The assistant intake endpoint internally composes:

Language detector (services.language_detector.detect_language)

Intake schema (services.app_server.schemas.intake.Intake)

Blueprint factory (blueprint_from_intake)

Content generator (services.agents.content_generator)

i18n message shaper (so the shape matches /v1/i18n/messages)

You can still call these APIs directly:

/v1/i18n/locales

/v1/i18n/messages (GET / POST)

/v1/i18n/translate

/v1/ai/chat

/v1/ai/summarize

The assistant endpoint is just a higher-level “one shot” that wires them together.