# Velu Brain – Local Runbook

This document explains how to run the **Velu brain** locally:

- FastAPI app server (API)
- SQLite job queue + worker
- Console assistant (React / Vite UI)
- End-to-end flow from idea → packaged ZIP → HTTP download

> **Ports (local convention)**
>
> - Velu API: **8010**
> - Velu console UI: **5178**
> - Generated apps (ZIP outputs) usually use:
>   - API: **8000**
>   - Web UI: **3000 / 3001**

---

## 1. Prerequisites

- Python 3.12
- Node.js + npm
- A virtualenv created in the repo:

```bash
cd ~/Downloads/velu
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

You can verify the codebase with:

pytest -q

2. Run the Velu API (8010)

From the repo root:

cd ~/Downloads/velu
source .venv/bin/activate

ENV=local \
API_KEYS=dev \
SECRET_KEY=dev-secret \
JWT_SECRET=dev-secret \
uvicorn services.app_server.main:app --reload --port 8010


This starts the Velu brain API on:

http://127.0.0.1:8010

Health checks:

curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/ready
curl http://127.0.0.1:8010/version

3. Run the worker

In a second terminal:

cd ~/Downloads/velu
source .venv/bin/activate

python -m services.queue.standalone_worker


You should see logs like:

worker: online db=/.../data/jobs.db


The worker will:

Poll the jobs SQLite DB

Execute tasks (e.g. packager, chat, etc.)

Write results back to the DB (used by /results/{job_id} and /tasks/recent)

4. Run the console assistant (CLI)

In a third terminal:

cd ~/Downloads/velu
source .venv/bin/activate
export PYTHONPATH=$PWD

python src/velu_console_assistant.py


You’ll see:

Velu console assistant
----------------------
Type an idea and press Enter.
Commands: 'q' / 'quit' to exit.


Example flow:

Idea> I want a web and mobile app for my shop. Web: Next.js admin dashboard and product catalog. Mobile: React Native app for customers to browse products and checkout. Use FastAPI backend, Postgres. Design style: colorful and friendly.

Running intake…

=== Product summary ===
type:       ecommerce
goal:       transactions
locales:    ['en']
channels:   ['web', 'ios', 'android']
frontend:   nextjs
backend:    fastapi
database:   postgres
plan_tier:  starter
plugins:    ['ecommerce']
module:     product
=======================

[enter]=new idea, 'd'=dump JSON, 'p'=packager, 'edit <rule>', 'ai <rule>', 'u'=undo, 'r'=redo, 'h'=history, 'e' or 'export [file]'=export blueprint, 'q'=quit
cmd> p


The p command enqueues a packager job via the API/queue and prints the result:

{
  "ok": true,
  "agent": "packager",
  "module": "product",
  "artifact_path": "/home/USER/Downloads/velu/artifacts/product.zip",
  "file_count": 90
}

5. HTTP download of artifacts from Velu API

With the API running on 8010 and the worker having produced product.zip, you can download the artifact via HTTP:

curl -v "http://127.0.0.1:8010/artifacts/product.zip" -o product.zip


You should see:

HTTP/1.1 200 OK

Security headers (CSP, X-Frame-Options, etc.)

product.zip created in your current directory.

This proves the full path is working:

console → /tasks → jobs DB → worker → artifact file → /artifacts/... → curl download

6. Unpack and run a generated app (ZIP)

From wherever you downloaded product.zip:

cd ~/Downloads
mkdir -p product_app
unzip product.zip -d product_app
cd product_app


Create a virtualenv and install deps:

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q || echo "no tests or basic exit-code from pytest is OK for now"


Run the generated FastAPI API (usually 8000 for generated apps):

uvicorn generated.services.api.app:app --reload --port 8000


Run the generated Next.js UI (often 3000 or 3001):

cd generated/web
npm install
npm run dev -- --port 3001


Open:

http://localhost:3001 (generated UI)

http://localhost:8000/health (generated API)

7. Velu console web UI (optional)

You can also run the Velu console React UI from velu-console/:

cd ~/Downloads/velu/velu-console
npm install
npm run dev -- --port 5178


Then open:

http://localhost:5178

This can be wired up to the same Velu API on 8010 (for now, the CLI assistant is the main “brain” front-end).

8. Security notes (local vs non-local)

In local / dev (ENV=local), we allow:

Flexible CORS (easy testing from different ports)

Simple API key (API_KEYS=dev)

In non-local (ENV=staging, ENV=prod):

SECRET_KEY and JWT_SECRET must be set

CORS can be tightened via CORS_ORIGINS / ALLOWED_ORIGINS

API authentication is enforced via API_KEYS or JWT configuration

See also:

docs/SECURITY.md

docs/RUNNING_VELU.md