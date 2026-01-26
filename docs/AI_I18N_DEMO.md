Velu AI + i18n Demo

This guide shows how to run the FastAPI demo API and exercise:

Multilingual content endpoints under /v1/i18n

AI chat / summarize endpoints under /v1/ai

Stub vs remote LLM backends

Everything works in stub mode by default (no API keys or network calls needed), so tests and local dev stay safe.

1. Prerequisites

Python 3.11+ (3.12 works)

A virtualenv with Velu installed (your .venv)

Recommended: Node.js 18+ if you want to run the Next.js frontend (optional for this demo)

From the repo root:

# Activate your virtualenv
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\activate   # Windows PowerShell


Verify everything is green:

pytest -q


Expected output:

189 passed, 1 skipped

2. Running the FastAPI app

The generated API lives in:

generated/services/api/app.py


Run it:

export PYTHONPATH=src:generated
uvicorn generated.services.api.app:app --reload --host 0.0.0.0 --port 8000


Windows PowerShell:

$env:PYTHONPATH = "src;generated"
uvicorn generated.services.api.app:app --reload --host 0.0.0.0 --port 8000


Visit:

http://localhost:8000

http://localhost:8000/docs

http://localhost:8000/redoc

3. i18n: Locales and Messages
3.1 List supported locales

Endpoint:

GET /v1/i18n/locales


Example:

curl http://localhost:8000/v1/i18n/locales


Typical response:

{
  "locales": ["en", "fr", "nl", "de", "ar", "ta"]
}

3.2 Get messages for a specific locale

Endpoint:

GET /v1/i18n/messages?locale=fr


Query param takes priority over headers.

Example:

curl "http://localhost:8000/v1/i18n/messages?locale=fr"


Response shape (simplified):

{
  "locale": "fr",
  "locales": ["en", "fr", "nl", "de", "ar", "ta"],
  "messages": {
    "fr": {
      "locale": "fr",
      "title": "Your App · A modern product experience",
      "sections": [
        {
          "id": "hero",
          "heading": "Your App · A modern product experience",
          "body": "Responsive, secure, and ready for production.",
          "primary_cta": "Commencer"
        }
      ]
    }
  },
  "summary": {
    "name": "Your App",
    "kind": "web_app",
    "locales": ["fr"]
  }
}

3.3 Content negotiation via Accept-Language

Endpoint:

GET /v1/i18n/messages


Rules:

If ?locale= is provided → wins.

Otherwise, the API parses Accept-Language:

Example header:

fr, en;q=0.8


If none match → fallback to "en".

Examples:

curl -H "Accept-Language: fr, en;q=0.8" http://localhost:8000/v1/i18n/messages

curl -H "Accept-Language: es-MX, fr;q=0.7" http://localhost:8000/v1/i18n/messages

curl -H "Accept-Language: zz, yy;q=0.5" http://localhost:8000/v1/i18n/messages

3.4 Create localized messages from a product spec

Endpoint:

POST /v1/i18n/messages


Example:

curl -X POST http://localhost:8000/v1/i18n/messages \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "name": "Inventory Manager",
      "locales": ["de", "ar"]
    }
  }'


Response (simplified):

{
  "locale": "de",
  "locales": ["ar", "de"],
  "messages": {
    "de": {
      "locale": "de",
      "title": "Inventory Manager · A modern product experience",
      "sections": [
        {
          "id": "hero",
          "heading": "Inventory Manager · A modern product experience",
          "body": "Responsive, secure, and ready for production.",
          "primary_cta": "Loslegen"
        }
      ]
    },
    "ar": {
      "locale": "ar",
      "title": "Inventory Manager · A modern product experience",
      "sections": [
        {
          "id": "hero",
          "heading": "Inventory Manager · A modern product experience",
          "body": "Responsive, secure, and ready for production.",
          "primary_cta": "ابدأ الآن"
        }
      ]
    }
  },
  "summary": {
    "name": "Inventory Manager",
    "kind": "web_app",
    "locales": ["ar", "de"]
  }
}

4. AI Endpoints (/v1/ai/*)

The AI system stays in stub mode unless you explicitly request a remote backend.

4.1 Chat — POST /v1/ai/chat

Example request:

{
  "messages": [
    {"role": "user", "content": "hello from velu ai demo"}
  ]
}


Example call:

curl -X POST http://localhost:8000/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello from velu ai demo"}]}'


Stub response:

{"reply": "hello from velu ai demo"}

4.2 Summarize — POST /v1/ai/summarize
curl -X POST http://localhost:8000/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"text":"this is some long text that should be summarized"}'


Stub behavior:

short text → return directly

long text → truncate + "..."

empty → ""

4.3 Models — GET /v1/ai/models

Example:

curl http://localhost:8000/v1/ai/models


Returns:

{
  "provider": "openai",
  "default_model": "gpt-4.1"
}

5. Stub vs Remote LLM

Stub mode is always used unless:

Request body includes "backend": "remote_llm"

AND environment variables are configured

AND services.llm.client successfully calls the remote API

Env vars:

VELU_REMOTE_LLM_PROVIDER=openai
VELU_REMOTE_LLM_MODEL=gpt-4.1
VELU_CHAT_MODEL=gpt-4.1
OPENAI_API_KEY=...

6. Quick Smoke Test

Start API:

export PYTHONPATH=src:generated
uvicorn generated.services.api.app:app --reload


Then test:

curl http://localhost:8000/v1/i18n/locales
curl http://localhost:8000/v1/i18n/messages?locale=fr
curl -X POST http://localhost:8000/v1/i18n/messages -d '{"product":{"name":"Test","locales":["de"]}}' -H "Content-Type: application/json"
curl -X POST http://localhost:8000/v1/ai/chat -d '{"messages":[{"role":"user","content":"hi"}]}' -H "Content-Type: application/json"
curl -X POST http://localhost:8000/v1/ai/summarize -d '{"text":"some long text"}' -H "Content-Type: application/json"
curl http://localhost:8000/v1/ai/models


When all work + pytest is green → the demo system is fully operational.

7. Troubleshooting
404 errors

Check:

API running on port 8000

You set PYTHONPATH=src:generated

Using correct URL paths

Test failures

Run:

pytest tests/test_i18n_api.py tests/test_i18n_negotiation.py tests/test_ai_demo.py -q


Everything must pass.

Remote backend not working

Remove "backend": "remote_llm" from calls → use stub

Check your API keys

Ensure services.llm.client is configured for your provider

### 3.5 Translate endpoint (stub)

You can also call a small translation helper.

Endpoint:

- `POST /v1/i18n/translate`

Request body:

```json
{
  "text": "Bonjour le monde",
  "target_locale": "en"
}
Rules:

If source_locale is provided, it is used as-is.

If source_locale is omitted, Velu uses the language detector to guess it.

The current backend is a deterministic stub: it returns the original text
with a [target] prefix (e.g. [en] Bonjour le monde).

The response shape:

json
Copy code
{
  "text": "Bonjour le monde",
  "translated_text": "[en] Bonjour le monde",
  "source_locale": "fr",
  "target_locale": "en",
  "backend": "stub"
}
vbnet
Copy code

## 8. Assistant-driven intake + pipeline

The `/v1/assistant/intake` endpoint ties everything together:

- Detect language from the idea text.
- Build a normalized Intake object (with `user_language` and product `locales`).
- Build a Blueprint with a `localization` block.
- Generate localized hero copy and sections via the content generator.
- Optionally enqueue a `pipeline` job to generate code.

Example:

```bash
curl -X POST http://localhost:8000/v1/assistant/intake \
  -H "Content-Type: application/json" \
  -d '{
    "company": { "name": "Acme Travel" },
    "product": {
      "type": "saas",
      "goal": "internal_tool",
      "locales": ["en", "fr"]
    },
    "idea": "tableau de bord pour mon équipe",
    "run_pipeline": true
  }'

Typical response shape (simplified):

{
  "ok": true,
  "language": "fr",
  "intake": { ... },
  "blueprint": {
    "id": "acme_travel",
    "localization": {
      "default_language": "en",
      "supported_languages": ["en", "fr"]
    }
  },
  "i18n": {
    "locales": ["en", "fr"],
    "messages": {
      "en": { ... },
      "fr": { ... }
    }
  },
  "pipeline_job_id": 636,
  "pipeline_module": "acme_travel"
}


Then inspect the job via the sqlite queue (for example, using
services.queue.sqlite_queue.load(pipeline_job_id) in a Python shell) or let your worker
process it and open the generated code for that module.