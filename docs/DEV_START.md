# Velu – Dev Start Guide

This file is a quick reference for running Velu in local dev.

## 1. Setup

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\activate  # Windows PowerShell

pip install -r requirements.txt  
pytest -q

should see something like:

191 passed, 1 skipped

2. Run the FastAPI app (API)

From the repo root:

source .venv/bin/activate
export PYTHONPATH=src:generated
uvicorn generated.services.api.app:app --reload --host 0.0.0.0 --port 8000


On Windows (PowerShell):

$env:PYTHONPATH = "src;generated"
uvicorn generated.services.api.app:app --reload --host 0.0.0.0 --port 8000


Then:

Open http://localhost:8000/docs to see the OpenAPI UI.

Try GET /v1/i18n/locales, GET /v1/i18n/messages, POST /v1/ai/chat, etc.

3. Run the Next.js web UI

From the repo root:

cd generated/web
npm install   # first time only
npm run dev


Then open:

http://localhost:3000

The home page calls the FastAPI app on http://localhost:8000/v1/i18n/messages.

4. Useful API checks

Quick smoke tests:

# Supported locales
curl http://localhost:8000/v1/i18n/locales

# Negotiated messages (GET)
curl "http://localhost:8000/v1/i18n/messages?locale=fr"

# Product-based messages (POST)
curl -X POST http://localhost:8000/v1/i18n/messages \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "name": "Inventory Manager",
      "locales": ["de", "ar"]
    }
  }'

# AI chat stub
curl -X POST http://localhost:8000/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "hello from velu ai demo"}
    ]
  }'

# AI summarize stub
curl -X POST http://localhost:8000/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "this is some long text that should be summarized by the ai stub endpoint"
  }'

5. Minimal test suite for AI + i18n

When changing anything related to i18n or AI endpoints, always run:

pytest tests/test_i18n_api.py \
       tests/test_i18n_negotiation.py \
       tests/test_ai_demo.py \
       tests/test_assistant_intake.py \
       tests/test_assistant_api.py -q


If those are green, the AI + i18n surface is still behaving as expected.
