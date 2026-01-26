# Running Velu (API + Worker + Console)

This document explains how to run the Velu system locally:

- **Velu API / app server** on port **8010**
- **Velu worker** that processes jobs and generates code / packages
- **Velu console UI** on port **5178**
- How **packaged ZIP files** are produced and how they’re used

---

## 0. Prerequisites

You only need a few tools:

- **Python** 3.11+ (3.12 recommended)
- **Node.js** 18+ (or 20+)
- **npm**
- (Optional) `pytest` for tests – but it’s already in requirements

All commands below assume you are in the Velu repo folder.

```bash
cd ~/Downloads/velu

1. Create and activate the virtualenv
cd ~/Downloads/velu

python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (PowerShell / CMD)

pip install -r requirements.txt


You only need to do pip install again when dependencies change.

2. Start the Velu worker

The worker consumes tasks from the SQLite jobs DB and performs things like
code generation, packaging, intake, etc.

In one terminal:

cd ~/Downloads/velu
source .venv/bin/activate

export VELU_ENABLE_PACKAGER=1
export TASK_DB="$PWD/data/jobs.db"

python -m services.worker.main


Keep this terminal open; this is your background worker.

3. Start the Velu API / app server (port 8010)

In a second terminal:

cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export API_KEYS="dev"              # simple dev key
export VELU_PIPELINE_MODE=multi    # recommended

uvicorn services.app_server.main:create_app --factory --port 8010


Health check:
curl http://localhost:8010/health

Recent tasks:
curl http://localhost:8010/tasks/recent

This API exposes:

/tasks – enqueue tasks like plan, pipeline, intake, packager, etc.

/results/{job_id} – fetch job results

/v1/i18n/* – i18n helper endpoints

/v1/assistant/intake – intake endpoint from “idea → blueprint + i18n”

/artifacts/{name} – download packaged ZIPs

4. Start the Velu Console UI (port 5178)

The console is a Vite + React app under velu-console/.

In a third terminal:

cd ~/Downloads/velu/velu-console
npm install         # first time only
npm run dev         # starts Vite on http://localhost:5178


Open your browser at:

http://localhost:5178

5. Connecting the console to the API

Inside the console UI you will see API URL and API Key fields.

For local dev:

API URL: http://127.0.0.1:8010

API Key: dev (this matches export API_KEYS="dev")

These values are stored locally in browser (localStorage), so  don’t
have to re-enter them every time.

6. What each console tab does
6.1 Velu queue

Tab: “Velu queue”

Submit tasks manually (plan, codegen, pipeline, intake, repo_summary)

Watch job results live

See generated files in a nice list

See Recent jobs coming from /tasks/recent

For packager jobs, you get a Download ZIP link directly

This uses endpoints like:

POST /tasks

GET /results/{job_id}?expand=1

GET /tasks/recent

GET /artifacts/{name}.zip

6.2 Assistant

Tab: “Assistant”

Simple chat-style assistant

describe what  need (“simple product website”, “mobile app”, etc.)

Assistant builds a spec, runs sub-jobs, and can trigger builds

Uses:

POST /assistant-chat (internally enqueues chat tasks)

The worker performs planning and code generation

6.3 Languages (i18n)

Tab: “Languages (i18n)”

Calls the i18n endpoints on port 8010:

GET /v1/i18n/locales

GET /v1/i18n/messages?locale=...

POST /v1/i18n/messages

POST /v1/i18n/translate

Useful to preview UI copy and test translation helpers.

6.4 Tasks demo & Inventory demo

These are example UIs that show how a simple frontend can talk to a backend
service:

Tasks demo: CRUD tasks, linked to a tasks_service API

Inventory demo: basic inventory operations, linked to inventory_service

They are mostly examples / demos and can be pointed at other APIs.

6.5 AI demo

Tab: “AI demo”

Exercises:

POST /v1/ai/chat

POST /v1/ai/summarize

GET /v1/ai/models

Shows how to pass backend selection + model names.

7. How ZIP packages are produced and used

When you ask Velu (via assistant or queue) to package a project, the worker
runs the packager agent. This:

walks relevant folders (generated/, src/, tests/, mobile/, etc.)

injects generated/services/app_server/ for a simple FastAPI entrypoint

writes a ZIP into the ./artifacts folder, named {module}.zip

adds a README in the ZIP with instructions for running API / web / mobile

In the console:

see a packager job in Recent

have a Download button that hits /artifacts/{module}.zip on 8010

7.1 What the client does with the ZIP

Typical client flow:

Download the ZIP from Velu (e.g. my_app.zip).

Extract it somewhere (e.g. ~/projects/my_app).

Open a terminal in that directory.

Follow the README inside the ZIP to:

create a Python virtualenv (if there is a Python backend)

run the API on port 8000 (FastAPI) or npm run dev (Node backend)

run the web frontend (Next.js on port 3001, React SPA, etc.)

run mobile apps (React Native / Flutter) if generated

run tests (pytest -q)

They do not need Velu’s worker or app server. The ZIP is a standalone project
they can customize and deploy however they want.

8. Common local development commands

Run tests:

cd ~/Downloads/velu
source .venv/bin/activate
pytest -q


Run only selected test groups, for example:

pytest tests/test_runtime_mobile.py tests/test_packager_mobile.py -q
pytest tests/test_rich_features_* -q

9. Summary

Port 8010: Velu app server (API)

Worker: python -m services.worker.main with VELU_ENABLE_PACKAGER=1

Port 5178: Velu console UI (Vite dev server)

ZIPs: generated into ./artifacts, downloadable via /artifacts/... and
come with their own README describing how to run API + web + mobile.

run all three (worker + API + console), get the full Velu experience:
from idea → intake → blueprint → code → package → downloadable project.