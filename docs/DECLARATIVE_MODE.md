# Velu Declarative Mode – Blueprints & Design

This document explains how to use Velu in **declarative mode**:

1. Start from a **high-level spec** (intake or hospital spec).
2. Convert it to a normalized **Blueprint**.
3. Turn the Blueprint into an **Architecture / Design summary**.
4. (Optionally) feed that into the **pipeline** to generate real apps.

---

## 0. Processes to run

From repo root:

### Velu API (task queue + blueprints endpoints)

```bash
cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export API_KEYS="dev"

uvicorn services.app_server.main:create_app --factory --port 8010

Health check:

curl http://127.0.0.1:8010/health

Worker

New terminal:

cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export VELU_ENABLE_PACKAGER=1

python -m services.worker.main

1. Blueprint model

The normalized Blueprint lives in:

services/app_server/schemas/blueprint.py

Key fields (simplified):

id: unique id for the product

name: human readable name

kind: "website" | "web_app" | "mobile_app" | "dashboard" | "api_only" | "cli" | "service"

frontend.framework: e.g. nextjs, react, vue, sveltekit

frontend.language: usually typescript or javascript

frontend.targets: list of targets, e.g. ["web"], ["android", "ios"], ["desktop"]

backend.framework: e.g. fastapi, django, express, nestjs

backend.language: python, node, other

backend.style: rest | graphql | rpc

database.engine: sqlite, postgres, mysql, mongodb, ...

database.mode: single_node | clustered

localization.default_language

localization.supported_languages: any languages (not just en, fr, nl)

This is the single canonical shape that everything else (design, pipeline, codegen) can consume.

2. Endpoint: /v1/blueprints/from-intake

Code:

services/app_server/routes/blueprints.py

services/app_server/schemas/intake.py

services/app_server/schemas/blueprint_factory.py

The /v1/blueprints/from-intake endpoint takes an Intake JSON (product + company) and returns:

company: the intake company section (echoed back)

product: the intake product section (echoed back)

blueprint: normalized Blueprint (dict)

Example:

curl -s -X POST http://127.0.0.1:8010/v1/blueprints/from-intake \
  -H "Content-Type: application/json" \
  -d '{
    "company": { "name": "Demo Co" },
    "product": {
      "type": "website",
      "goal": "lead_gen",
      "audiences": ["customers"],
      "channels": ["web"],
      "locales": ["en", "fr"]
    }
  }' | jq


Expected shape (simplified):

{
  "company": { "name": "Demo Co" },
  "product": {
    "type": "website",
    "goal": "lead_gen",
    "audiences": ["customers"],
    "channels": ["web"],
    "locales": ["en", "fr"]
  },
  "blueprint": {
    "id": "demo_co",
    "name": "Demo Co website",
    "kind": "website",
    "frontend": {
      "framework": "nextjs",
      "language": "typescript",
      "targets": ["web"]
    },
    "backend": { "...": "..." },
    "database": { "...": "..." },
    "localization": {
      "default_language": "en",
      "supported_languages": ["en", "fr"]
    }
  }
}


Used by tests:

tests/test_blueprint_from_intake.py

tests/test_blueprint_api.py::test_blueprint_from_intake_endpoint_basic

3. Endpoint: /v1/blueprints/from-hospital

This endpoint handles a richer spec for complex apps (like hospital management).

Code:

services/app_server/routes/blueprints.py

services/app_server/schemas/blueprint_factory.py (blueprint_from_hospital_spec)

Input: a full spec like:

{
  "project": {
    "id": "hospital_mgmt_v1",
    "name": "Hospital Management Web App",
    "type": "web_app",
    "description": "demo hospital app"
  },
  "stack": {
    "frontend": {
      "framework": "nextjs",
      "language": "typescript",
      "ui_library": "tailwind_shadcn"
    },
    "backend": {
      "framework": "fastapi",
      "language": "python",
      "style": "rest"
    },
    "database": {
      "engine": "sqlite",
      "mode": "single_node"
    }
  },
  "localization": {
    "default_language": "en",
    "supported_languages": ["en", "fr", "nl", "de", "ar", "ta"]
  },
  "features": {
    "modules": ["patients", "appointments", "doctors", "dashboard"],
    "auth": {
      "enabled": true,
      "roles": ["patient", "staff", "admin"],
      "login_methods": ["email_password"]
    }
  }
}


Call:

curl -s -X POST http://127.0.0.1:8010/v1/blueprints/from-hospital \
  -H "Content-Type: application/json" \
  -d @hospital_spec.json | jq


Response fields:

product – simplified product summary derived from project + localization

stack – stack section echoed from the spec

blueprint – normalized Blueprint (dict)

Used by tests:

tests/test_blueprint_from_hospital_spec.py

tests/test_blueprint_api.py::test_blueprint_from_hospital_endpoint_basic

4. Endpoint: /v1/blueprints/design

This is the key declarative design endpoint.

Code:

services/app_server/routes/blueprints.py (design_endpoint)

services/agents/api_design.py (logic that builds the architecture summary)

Input: a full Blueprint JSON, for example:

curl -s -X POST http://127.0.0.1:8010/v1/blueprints/design \
  -H "Content-Type: application/json" \
  -d '{
    "id": "demo_app",
    "name": "Demo App",
    "kind": "web_app",
    "frontend": { "framework": "nextjs", "language": "typescript", "targets": ["web"] },
    "backend": { "framework": "fastapi", "language": "python", "style": "rest" },
    "database": { "engine": "sqlite", "mode": "single_node" },
    "localization": { "default_language": "en", "supported_languages": ["en","fr"] }
  }' | jq


Response:

blueprint: normalized Blueprint (echoed)

architecture: containing:

core fields (id, name, kind, frontend, backend, database, localization)

summary: a human-readable multi-line description of the architecture

Example (simplified):

{
  "blueprint": { "...": "..." },
  "architecture": {
    "id": "demo_app",
    "name": "Demo App",
    "kind": "web_app",
    "frontend": { "...": "..." },
    "backend": { "...": "..." },
    "database": { "...": "..." },
    "localization": { "...": "..." },
    "summary": "Architecture for Demo App (web_app)\n\nFrontend:\n  - Framework: nextjs\n  - Language: typescript\n  - Targets: ['web']\n\nBackend:\n  - Framework: fastapi\n  - Language: python\n  - Style: rest\n\nDatabase:\n  - Engine: sqlite\n  - Mode: single_node\n\nLocalization:\n  - Default: en\n  - Supported: ['en', 'fr']\n\nHigh-Level Components:\n  - API layer\n  - Business logic layer\n  - Data layer\n  - Auth module\n  - Localization middleware\n\nSuggested Deployment:\n  - Docker compose (web + api + db)\n  - Alternative: serverless (Vercel + managed DB)"
  }
}


Used by tests:

tests/test_blueprint_design_api.py

5. Blueprint persistence

Blueprints are stored in SQLite so they can be reused later.

Code:

services/app_server/blueprints_sqlite.py

services/app_server/routes/blueprints.py (save_endpoint, get_endpoint, list_blueprints_api)

Endpoints:

Save a blueprint:

curl -s -X POST http://127.0.0.1:8010/v1/blueprints/save \
  -H "Content-Type: application/json" \
  -d '{
    "id": "demo_app",
    "name": "Demo App",
    "kind": "web_app",
    "frontend": { "framework": "nextjs", "language": "typescript", "targets": ["web"] },
    "backend": { "framework": "fastapi", "language": "python", "style": "rest" },
    "database": { "engine": "sqlite", "mode": "single_node" },
    "localization": { "default_language": "en", "supported_languages": ["en","fr"] }
  }' | jq


Get a blueprint:

curl -s http://127.0.0.1:8010/v1/blueprints/demo_app | jq


List blueprints:

curl -s "http://127.0.0.1:8010/v1/blueprints?limit=20" | jq

6. Hospital demo: hospital_codegen + team_dashboard_api

The hospital demo shows how a rich spec can be turned into a working API + tests.

Pieces:

Agent: services/agents/hospital_codegen.py

Generated API: team_dashboard_api.py

Tests: tests/test_team_dashboard_api.py

High-level test: tests/test_team_dashboard.py

Run tests:

cd ~/Downloads/velu
source .venv/bin/activate
pytest -q


Run the demo API:

cd ~/Downloads/velu
source .venv/bin/activate
uvicorn team_dashboard_api:app --reload --port 8300


Basic checks:

curl -s http://127.0.0.1:8300/health | jq
curl -s http://127.0.0.1:8300/patients | jq
curl -s http://127.0.0.1:8300/appointments | jq
curl -s http://127.0.0.1:8300/dashboard/overview | jq

7. How this connects to the future Velu Assistant

With declarative mode in place, the future flow for Velu is:

User talks to the assistant in natural language (what they want to build).

Assistant builds a spec (intake or hospital-style).

Backend converts spec → Blueprint via:

/v1/blueprints/from-intake or

/v1/blueprints/from-hospital

Blueprint goes into /v1/blueprints/design to produce an Architecture summary.

That architecture + blueprint feeds into the existing pipeline to generate:

Frontend (Next.js, React, Flutter, Tauri, etc.)

Backend (FastAPI, Node, etc.)

Database (SQLite, Postgres, etc.)

Multi-language UI (any languages: en, fr, nl, de, ar, ta, …)

Packager turns builds into runnable projects for:

Linux, macOS, Windows (and, in the future, mobile / desktop targets).