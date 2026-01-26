🧠 Velu — Task Orchestrator & Project Builder

FastAPI-based task queue, routing, and policy evaluation system with Prometheus monitoring.
Self-hosted, multi-agent AI pipeline that plans → codes → tests → secures → builds → deploys → monitors.

🚀 Overview

Velu is a local, offline-capable AI system that:

Accepts natural-language instructions

Generates product specifications

Plans builds

Produces code/tests (Next.js frontend + FastAPI backend)

Stores session specs

Generates a landing page

Lets you run the generated web UI locally

🧩 System Architecture (short)
Component	Description
FastAPI App Server	Receives chat messages, creates jobs, exposes REST API.
Worker	Consumes queued jobs and performs planning/building.
Rules Engine	Converts chat into structured product specs.
Generated Code	Lives under generated/ (Next.js + FastAPI).
Landing Sync	Generates a clean UI landing page based on the final spec.
Prometheus	Metrics gathering (optional).
🛠️ Local Development
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/test.sh

🔐 Prometheus Basic Auth

Prometheus scrapes /metrics through Caddy.

cp monitoring/prom_basic_pass.txt.example monitoring/prom_basic_pass.txt
echo "my-strong-password" > monitoring/prom_basic_pass.txt

▶️ Running Velu Locally (App Server + Worker)
1. Start the app server
cd ~/Downloads/velu
source .venv/bin/activate

TASK_DB="$PWD/data/jobs.db" \
uvicorn services.app_server.main:create_app --factory --port 8010

2. Start the worker
cd ~/Downloads/velu
source .venv/bin/activate

TASK_DB="$PWD/data/jobs.db" \
PYTHONUNBUFFERED=1 python -m services.worker.main


App server → handles chat
Worker → actually runs build jobs

💬 Creating a New Project With Velu (Chat → Build → Code)

Everything starts with POST /assistant-chat.

Start a fresh session
curl -X POST "http://127.0.0.1:8010/assistant-chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{
    "message": "",
    "session_id": "shop_v3",
    "backend": "rules",
    "reset": true
  }'


Velu will ask you:

What do you want to build?

Main goal

Features

Pages

Target users

Visual style

Project name → used as module name

Example answers
"Website"
"online store for clothing"
"show products, cart, checkout, user accounts"
"Home, Products, Product detail, Cart, Checkout, Account"
"customers, admins"
"clean and minimal"
"shop_v3"

Start the build
curl -X POST "http://127.0.0.1:8010/assistant-chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{
    "message": "build",
    "session_id": "shop_v3",
    "backend": "rules"
  }'


Velu returns a job_id, e.g. 164.

Check build status
curl "http://127.0.0.1:8010/results/164?expand=1"


When status="done" → the project is generated.

Generated code appears under:

generated/services/
generated/web/

🎨 Sync Landing Page (Auto UI Summary)

Run:

cd ~/Downloads/velu
source .venv/bin/activate

python -m src.landing_sync --session-id shop_v3


This updates:

generated/web/pages/index.tsx


No manual edits needed.

🌐 Run the Next.js Frontend
cd ~/Downloads/velu/generated/web
npm install     # only first time
npm run dev -- --port 3001


Open:

👉 http://localhost:3001