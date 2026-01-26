# Velu – Developer Handbook

This document explains how to run Velu locally, how the chat assistant works, and which files are safe to change when evolving the system (for humans or future ChatGPT sessions).

---

## 1. How Velu works (high level)

Flow:

1. You talk to Velu in the **console UI** (`velu-console`).
2. The console sends messages to the **FastAPI backend** (`services.app_server.app`).
3. The backend uses the **chat agent** (`services/agents/chat.py`) to:
   - keep a per-session JSON spec,
   - ask follow-up questions,
   - decide plan tier (starter / pro / enterprise),
   - enqueue jobs (intake, packager).
4. A **worker process** (`services.worker`) reads jobs from a SQLite queue (`data/jobs.db`) and runs:
   - **intake**: planning + codegen (blueprints, scaffolds),
   - **packager**: builds the final ZIP for the client.
5. The ZIP contains backend, frontend(s), tests, and customer-facing docs.

---

## 2. Running Velu locally

### 2.1 Python environment

```bash
cd ~/Downloads/velu
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt

2.2 API server (FastAPI)

Default:

uvicorn services.app_server.app:app --reload --port 8010

If you prefer another port:

uvicorn services.app_server.app:app --reload --port 8010


Key endpoints (for debugging):

GET /health – basic health check

POST /v1/assistant/chat (or /v1/chat depending on version) – chat endpoint

POST /v1/assistant/intake – structured intake → blueprint

2.3 Worker (jobs: intake, packager, etc.)
cd ~/Downloads/velu
source .venv/bin/activate
python -m services.worker


The worker reads from data/jobs.db and executes:

task="intake" → planning + generation

task="packager" → build ZIP into artifacts/<module>.zip

2.4 Console UI (Velu console)

The console lives in velu-console/ (React / Vite).

cd ~/Downloads/velu/velu-console
npm install
npm run dev -- --port 5178


Then open:

http://localhost:5178

Make sure the console knows which API base URL to use (usually http://127.0.0.1:8000 or http://127.0.0.1:8010).

3. Chat backends: rules / local_llm / remote_llm

All logic lives in services/agents/chat.py.

3.1 Backend selection

Allowed values:

"rules" (default)

"local_llm"

"remote_llm"

Determined by:

backend field in the JSON payload from console, or

VELU_CHAT_BACKEND environment variable.

3.2 rules backend (default, deterministic)
def _run_rules_backend(session, msg) -> str:
    return _next_question(session, msg)


Uses _next_question only.

Pure Python, no API calls.

Drives the spec-building wizard.

Safe and used by tests.

3.3 local_llm backend

Currently:

def _call_local_llm(session, msg) -> str:
    return _next_question(session, msg)


Placeholder: behaves exactly like rules.

Later can be wired to a local model (Ollama, LM Studio, etc.).

Logic must still be rules-first; model only rewrites wording.

3.4 remote_llm backend
def _call_remote_llm(session, msg) -> str:
    draft = _next_question(session, msg)
    # send draft + instructions to remote LLM via services.llm.client
    # if it fails, fall back to draft


Always computes a rules-based draft first.

Remote model only rewrites the reply (no logic).

On error, the user still gets the rules reply.

4. The spec, modes and plan tiers

The chat agent keeps a per-session spec in session["spec"].
Key fields:

product_type: "website" | "web_app" | "dashboard" | "mobile_app" | "ecommerce" | ...

goal: rich free-text goal / description

main_features: list of features

pages: list of pages

target_users: who uses it

platform: "web" or "mobile"

frontend: "nextjs" | "react" | "vue" | "flutter" | ...

backend: "fastapi" | "node" | "django" | ...

database: "sqlite" | "postgres" | "mysql" | "mongodb" | "none"

roles: domain roles (admin, manager, customer, etc.)

user_flows: key flows / journeys

plugins: building blocks (auth, subscriptions, billing, etc.)

compliance: e.g. ["GDPR", "multi_tenant"]

assistant_mode: "basic" | "pro" | "architect"

security_posture: "standard" | "hardened"

plan_tier: "starter" | "pro" | "enterprise"

module_name: slug used for folders and package names

4.1 Mode + security detection

From the goal text, chat.py decides:

assistant_mode = "basic" | "pro" | "architect"
security_posture = "standard" | "hardened"


Signals:

SaaS, multi-tenant, subscriptions, tenants → architect

dashboards, analytics, KPIs → pro

SSO/Okta/AzureAD, audit logs, IP allowlist, GDPR/HIPAA/PCI → hardened

4.2 Plan tier

plan_tier is derived from (assistant_mode, security_posture):

basic + standard → starter

pro or architect + standard → pro

architect + hardened → enterprise

Then _normalize_tier_fields(spec):

normalizes assistant_mode, security_posture, plan_tier

enforces Enterprise ⇒ Postgres (no SQLite)

adjusts plugins and compliance, e.g.:

Starter: strips subscriptions/billing, no multi-tenant compliance

Pro: ensures auth, but still single-tenant by default

Enterprise: ensures auth, subscriptions, billing, adds multi_tenant compliance

5. Build pipeline (intake + packager)
5.1 Starting a build

In chat.py, _start_build(session):

Reads:

kind ← spec["product_type"]

idea ← spec["goal"]

frontend / backend / database

module ← spec["module_name"]

plan_tier ← spec["plan_tier"]

Enqueues:

intake_job_id = q.enqueue(
    task="intake",
    payload={
        "kind": kind,
        "idea": idea,
        "frontend": frontend,
        "backend": backend,
        "database": database,
        "module": module,
        "schema": {},
        "session_id": session_id,
        "plan_tier": plan_tier,
    },
)


Optionally enqueues task="packager" if VELU_ENABLE_PACKAGER=1.

5.2 Packager and tier-aware ZIPs

In services/agents/packager.py, handle(payload):

Reads:

module

kind, backend, database

plan_tier (starter | pro | enterprise)

Writes ZIP to artifacts/<module>.zip.

Always adds:

README_packaged.md, README.md

README_client.md (tier label + run instructions)

README_developer.md (backend, frontend, DB, plan tier + API/worker/console commands)

Dockerfile_packaged, docker-compose.packaged.yml

DEPLOYMENT_GUIDE.md

ENVIRONMENT_VARIABLES.md

SUPPORT_AND_WARRANTY.md

PRIVACY_POLICY_template.md

TERMS_template.md

COOKIES_POLICY_template.md

DATA_PROCESSING_ADDENDUM_template.md

Tier-specific:

Starter:

No SECURITY.md (or very minimal)

No GDPR_DATA_REQUESTS_template.md

Pro:

SECURITY.md with standard security guidance

Possibly more GDPR helpers later

Enterprise:

SECURITY.md with hardened / multi-tenant notes

GDPR_DATA_REQUESTS_template.md

Stronger Postgres / multi-tenant expectations in docs

6. Files that future ChatGPT sessions may safely modify

When you ask a new ChatGPT to extend Velu, point it to this list.

6.1 Core assistant + spec

services/agents/chat.py

Conversation flow (_next_question)

Spec editing (_update_spec_from_freeform, _apply_spec_edits_from_text)

Tier logic (_detect_mode_and_security, _normalize_tier_fields, _derive_plan_tier)

Build trigger (_start_build)

Backend selection (rules / local_llm / remote_llm)

services/app_server/schemas/intake.py

services/app_server/schemas/blueprint.py

services/app_server/schemas/blueprint_factory.py

services/app_server/routes/assistant.py

6.2 Packager & generated ZIP contents

services/agents/packager.py

Which files go into the ZIP

Tier-aware docs and security files

src/landing_sync.py (glue between spec and landing content)

6.3 Console UI

velu-console/src/App.jsx

Chat panel

Product summary (including plan tier, assistant mode, security posture)

Help tab (explaining tiers, ports, etc.)

6.4 Queue and worker (for new job types)

services/queue/sqlite_queue.py

services/worker_router.py (or similar router file)

services/agents/<new_agent>.py (for future tasks like pipeline_autofix)

6.5 Files to avoid changing automatically

tests/ – only modify deliberately when updating behavior.

generated/ inside the Velu repo – this is demo output.

Root pyproject.toml / requirements.txt – changing dependencies may break tests.

Anything under artifacts/ or data/ – these are runtime outputs.

7. Keeping tests green

From the Velu root:

cd ~/Downloads/velu
source .venv/bin/activate
pytest -q


Currently: 230+ tests passed, 1 skipped.

When evolving Velu:

Prefer adding new functions / branches instead of rewriting core behavior.

If you change chat flow, verify:

tests/test_console_app.py

tests/test_assistant_pipeline.py (if present)

If you change packager, check:

tests/test_packager_demo_mod.py

tests/test_packager_multi_frontends.py

tests/test_packager_node_backend.py

Velu’s goal:

You describe a product → Velu behaves like a product manager + architect + dev team → you get a runnable, testable, deployable project ZIP with docs and legal templates.

This handbook should give humans (and future AIs) a clear map of where to plug new features without breaking that contract.


Save and exit.

---

## 2. Quick sanity check

Just to be sure nothing accidentally broke:

```bash
cd ~/Downloads/velu
source .venv/bin/activate
pytest -q

