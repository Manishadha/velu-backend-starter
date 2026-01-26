# Velu Multistack Demo – Runbook

## Processes and ports

- Velu API (task queue): `http://127.0.0.1:8010`
- Worker: consumes jobs from `data/jobs.db`
- Generated FastAPI demo API: `http://127.0.0.1:8203`
- Next.js app (generated/web): `http://localhost:3006`
- React SPA (react_spa): `http://localhost:3010`
- Velu Console (velu-console): `http://127.0.0.1:5178`

## 1. Velu API (task queue)

```bash
cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export API_KEYS="dev"

uvicorn services.app_server.main:create_app --factory --port 8010


Health check:

curl http://127.0.0.1:8010/health

2. Worker

Open a new terminal:

cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export VELU_ENABLE_PACKAGER=1

python -m services.worker.main


The worker prints logs like:

worker: online db=/.../data/jobs.db
worker: done 378
worker: done 379

3. Generated FastAPI demo API

Open a new terminal:

cd ~/Downloads/velu
source .venv/bin/activate

uvicorn generated.services.api.app:app --reload --port 8203


Basic checks:

# Health
curl http://127.0.0.1:8203/health

# i18n locales
curl http://127.0.0.1:8203/v1/i18n/locales


Auth check:

# Issue a demo token
TOKEN=$(curl -s "http://127.0.0.1:8203/v1/auth/token?sub=me@example.com" | jq -r .access_token)

# Call protected endpoint
curl -s http://127.0.0.1:8203/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"


Expected response:

{
  "id": "me@example.com",
  "email": "me@example.com",
  "roles": ["user"]
}


AI stub endpoints:

# Chat
curl -s -X POST http://127.0.0.1:8203/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      { "role": "user", "content": "hello from velu ai demo" }
    ]
  }'

# Summarize
curl -s -X POST http://127.0.0.1:8203/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "this is some long text that should be summarized by the ai stub endpoint"
  }'


Security headers check:

curl -s -D - http://127.0.0.1:8203/health -o /dev/null


Headers include:

X-Content-Type-Options: nosniff

Referrer-Policy: strict-origin-when-cross-origin

X-Frame-Options: DENY

Cross-Origin-Opener-Policy: same-origin

Cross-Origin-Resource-Policy: same-origin

Permissions-Policy: geolocation=(), microphone=()

Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'

4. Next.js app (generated/web)

Open a new terminal:

cd ~/Downloads/velu/generated/web
npm install
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8203 npm run dev -- --port 3006


Open in browser:

http://localhost:3006

The page:

Reads locales from http://127.0.0.1:8203/v1/i18n/locales

Shows selectable language codes

Falls back to defaults if the API is unavailable

5. React SPA (react_spa)

Open a new terminal:

cd ~/Downloads/velu/react_spa
npm install
npm run dev -- --port 3010


Open in browser:

http://localhost:3010

The SPA:

Reads locale definitions from react_spa/i18n.locales.json

Shows all supported languages (e.g. en, fr, nl, de, ar, ta)

6. Velu Console

Open a new terminal:

cd ~/Downloads/velu/velu-console
npm install
npm run dev


Open in browser:

http://127.0.0.1:5178/

Useful tabs:

Velu queue – run tasks like pipeline, repo_summary, packager

Assistant – chat with the Velu assistant using rules, local_llm, or remote_llm

Tasks demo – calls tasks_service

Inventory demo – calls inventory_service

7. Pipeline in multi-step mode

Enable multi-step agent pipeline:

export VELU_PIPELINE_MODE=multi


Example job:

curl -s -X POST http://127.0.0.1:8010/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{
    "task": "pipeline",
    "payload": {
      "idea": "AI demo app",
      "module": "ai_demo",
      "frontend": "nextjs",
      "backend": "fastapi",
      "database": "sqlite",
      "kind": "app"
    }
  }'


Recent tasks:

curl -s http://127.0.0.1:8010/tasks/recent | jq


The pipeline enqueues:

requirements

architecture

datamodel

api_design

ui_scaffold

backend_scaffold

ai_features

security_hardening

testgen

These subjobs can be inspected and applied via:

python scripts/apply_result_files.py <job_id>


## Hospital team dashboard API demo (declarative → code)

This demo comes from a hospital spec sent to the `hospital_codegen` agent and
is implemented in `team_dashboard_api.py`.

### Start the API

```bash
cd ~/Downloads/velu
source .venv/bin/activate

uvicorn team_dashboard_api:app --reload --port 8300
The service runs at: http://127.0.0.1:8300

Smoke checks
bash
Copy code
# Health
curl -s http://127.0.0.1:8300/health | jq

# Patients list
curl -s http://127.0.0.1:8300/patients | jq

# Appointments list
curl -s http://127.0.0.1:8300/appointments | jq

# Dashboard overview
curl -s http://127.0.0.1:8300/dashboard/overview | jq
Expected responses (shape only):

/health → {"ok": true, "service": "team_dashboard_api"}

/patients → list of demo patients

/appointments → list of demo appointments

/dashboard/overview → totals + appointments_by_status

