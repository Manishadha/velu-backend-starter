# Multistack Blueprints

## 1. Overview

Velu uses a `Blueprint` model to describe the target stack for a generated project:

- **Frontend** framework (Next.js, React SPA, React Native, …)
- **Backend** framework (FastAPI, Express, Django, …)
- **Database** (SQLite, Postgres, …)
- **Localization** (languages)
- **Targets / platforms** (web, android, ios, desktop)

The blueprint is produced from either:

- the Intake form (`services/app_server/schemas/intake.py`) via  
  `blueprint_from_intake(intake)`
- a “hospital spec” dict via  
  `blueprint_from_hospital_spec(spec)`


## 2. Supported stacks (current behavior)

### 2.1 Frontend

`BlueprintFrontend` fields:

```python
class BlueprintFrontend(BaseModel):
    framework: str = "nextjs"
    language: str = "typescript"
    targets: list[Literal["web", "android", "ios", "desktop"]] = Field(
        default_factory=lambda: ["web"]
    )

Typical framework values:

nextjs (default web stack)

react (React SPA via Vite)

react_native (mobile)

flutter (mobile)

tauri, electron (desktop-style UIs)

targets describe where the frontend is meant to run:

web

android

ios

desktop

Automatic target selection (in blueprint_from_hospital_spec)

If kind == "mobile_app" or frontend.framework is react_native/flutter
→ targets = ["android", "ios"]

If frontend.framework is tauri or electron
→ targets = ["desktop"]

Otherwise
→ targets = ["web"]

2.2 Backend

BlueprintBackend fields:

class BlueprintBackend(BaseModel):
    framework: str = "fastapi"
    language: str = "python"
    style: Literal["rest", "graphql", "rpc"] = "rest"


Typical framework values:

fastapi (default)

django

express

nestjs

others as needed

Language resolution in blueprint_from_hospital_spec:

fastapi, django → language = "python"

express, nestjs, node → language = provided language or "node"

anything else → language = provided language or "python"

style:

"rest" (default)

"graphql"

"rpc"

2.3 Database

BlueprintDatabase fields:

class BlueprintDatabase(BaseModel):
    engine: str = "sqlite"
    mode: Literal["single_node", "clustered"] = "single_node"


Examples:

engine: sqlite, postgres, mysql, mongodb, …

mode: "single_node" (default) or "clustered"

2.4 Localization
class BlueprintLocalization(BaseModel):
    default_language: str = "en"
    supported_languages: list[str] = Field(default_factory=lambda: ["en"])

3. From Intake → Blueprint

Function:
services/app_server/schemas/blueprint_factory.py::blueprint_from_intake

What it does:

Reads intake.product.type and normalizes it into one of:

website | web_app | mobile_app | dashboard | api_only | cli | service


Reads intake.product.channels and converts to targets via _targets_from_channels:

if empty / None → defaults to ["web"]

for kind == "mobile_app":

includes android, ios as needed

for other kinds:

can include web, android, ios, desktop

Localization:

default_language = first locale if present, otherwise "en"

supported_languages = all locales if present, otherwise ["en"]

Sketch example (not tied to tests):

from services.app_server.schemas.intake import Intake, Company, Product
from services.app_server.schemas.blueprint_factory import blueprint_from_intake

intake = Intake(
    company=Company(name="Velu Shop"),
    product=Product(
        name="Merch Store",
        type="web_app",
        channels=["web"],
        locales=["en", "fr"],
        # ... other fields as required by Intake ...
    ),
)

bp = blueprint_from_intake(intake)

assert bp.kind == "web_app"
assert bp.frontend.framework == "nextjs"
assert bp.frontend.targets == ["web"]
assert bp.localization.default_language == "en"
assert bp.localization.supported_languages == ["en", "fr"]

4. From Hospital Spec → Blueprint

Function:
services/app_server/schemas/blueprint_factory.py::blueprint_from_hospital_spec

The spec is a dict that typically has:

"project": high-level info

"stack": frontend/backend/database

"localization": languages

4.1 Example #1 – Web dashboard (Next.js + FastAPI + SQLite)

This example is covered by a unit test:
tests/test_multistack_blueprints_examples.py::test_doc_example_web_dashboard_spec

from services.app_server.schemas.blueprint_factory import blueprint_from_hospital_spec

spec = {
    "project": {
        "id": "team_dashboard",
        "name": "Team Dashboard",
        "type": "dashboard",
    },
    "stack": {
        "frontend": {
            "framework": "nextjs",
            "language": "typescript",
        },
        "backend": {
            "framework": "fastapi",
            "language": "python",
            "style": "rest",
        },
        "database": {
            "engine": "sqlite",
            "mode": "single_node",
        },
    },
    "localization": {
        "default_language": "en",
        "supported_languages": ["en", "fr"],
    },
}

bp = blueprint_from_hospital_spec(spec)
print(bp.dict())


Resulting key fields:

bp.id == "team_dashboard"

bp.name == "Team Dashboard"

bp.kind == "dashboard"

Frontend:

bp.frontend.framework == "nextjs"

bp.frontend.language == "typescript"

bp.frontend.targets == ["web"]

Backend:

bp.backend.framework == "fastapi"

bp.backend.language == "python"

bp.backend.style == "rest"

Database:

bp.database.engine == "sqlite"

bp.database.mode == "single_node"

Localization:

bp.localization.default_language == "en"

bp.localization.supported_languages == ["en", "fr"]

4.2 Example #2 – Mobile app (React Native + Express + Postgres)

This example is also covered by a unit test:
tests/test_multistack_blueprints_examples.py::test_doc_example_mobile_multiplatform_spec

from services.app_server.schemas.blueprint_factory import blueprint_from_hospital_spec

spec = {
    "project": {
        "id": "shopping_app",
        "name": "Shopping App",
        "type": "mobile_app",
    },
    "stack": {
        "frontend": {
            "framework": "react_native",
            "language": "typescript",
        },
        "backend": {
            "framework": "express",
            "language": "typescript",
            "style": "rest",
        },
        "database": {
            "engine": "postgres",
            "mode": "clustered",
        },
    },
    "localization": {
        "default_language": "nl",
        "supported_languages": ["nl", "en", "fr"],
    },
}

bp = blueprint_from_hospital_spec(spec)
print(bp.dict())


Resulting key fields:

bp.id == "shopping_app"

bp.name == "Shopping App"

bp.kind == "mobile_app"

Frontend:

bp.frontend.framework == "react_native"

bp.frontend.language == "typescript"

because this is a mobile app:

bp.frontend.targets == ["android", "ios"]

Backend:

bp.backend.framework == "express"

bp.backend.language == "typescript"

bp.backend.style == "rest"

Database:

bp.database.engine == "postgres"

bp.database.mode == "clustered"

Localization:

bp.localization.default_language == "nl"

bp.localization.supported_languages == ["nl", "en", "fr"]

5. How Velu uses the Blueprint

In higher-level agents / services:

Build an Intake or a hospital spec from the user’s description.

Convert to a Blueprint:

bp = blueprint_from_intake(intake)
# or
bp = blueprint_from_hospital_spec(spec)


Use bp to decide:

Which frontend scaffold to generate:

nextjs vs react vs react_native, etc.

Which backend scaffold to generate:

fastapi, express, django, …

How to configure the database:

sqlite vs postgres, single-node vs clustered.

Which platforms to target:

web, android, ios, desktop.

6. Running a generated project (example)

For a generated project similar to product_catalog_web_1, you typically have:

A backend API (FastAPI)

An app server (Velu’s control plane)

A frontend (Next.js or React)

Typical commands (adjust ports and module paths as per the generated README):

# From the root of the generated project
source .venv/bin/activate

# 1) Backend API (FastAPI)
uvicorn generated.services.api.app:app --reload --port 8001
# or, if a __main__ is wired:
# python -m generated.services.api.app

# 2) App server (Velu app server)
python -m generated.services.app_server.main

# 3) Next.js frontend
cd generated/web
npm install
npm run dev -- --port 3001


Then open in your browser:

API docs: http://127.0.0.1:8001/docs

Web UI: http://127.0.0.1:3001

Note: exact module paths and ports may vary for each generated project.
Always check the README in the generated package/zip for the final commands.