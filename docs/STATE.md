# Velu State

Last updated: 2025-12-21 at 9.00 AM

## Goal

Run Velu locally (Docker Compose) with:
- Postgres backend (jobs_v2)
- DB-backed API keys (scoped)
- Multi-tenant orgs
- Actor stamping on jobs
- Plan enforcement (base/hero/superhero)

## Current Runtime

- API: services/app_server/main.py (FastAPI)
- Auth middleware: services/app_server/auth.py (DB-backed api_keys lookup)
- Scopes dependency: services/app_server/dependencies/scopes.py
- Plan dependency: services/app_server/dependencies/plan.py
- Jobs backend: services/queue/jobs_sqlite.py
  - Postgres: jobs_v2
  - SQLite: legacy jobs table
- Worker loop: services/queue/worker_entry.py

## Data / Volumes

- /data : persistent app data (dev_api_keys.env written here)
- /git : repo working area
- /workspace : job workspace isolation

Docker volumes:
- velu-data -> /data
- velu_git-data -> /git
- velu_workspace-data -> /workspace
- velu_pgdata -> Postgres data dir

## Migrations

- Runner: services/db/migrate.py
- Source: services/db/migrations/*.sql
- Trigger: services/app_server/main.py calls migrate() when VELU_RUN_MIGRATIONS=1
- Postgres schema table: schema_migrations

## API Keys and Hashing

Single source of truth hashing:
- services/app_server/models/api_key.py
  - env: VELU_API_KEY_PEPPER
  - sha256(pepper + raw) -> base64url -> strip "="

Auth lookup hashing:
- services/app_server/auth.py uses the same pepper env name: VELU_API_KEY_PEPPER

Key management:
- services/auth/api_keys.py creates/list/revoke/rotate DB keys
- Admin router:
  - services/app_server/admin.py
  - Endpoints:
    - POST /admin/api-keys
    - GET /admin/api-keys
    - POST /admin/api-keys/{id}/revoke
    - POST /admin/api-keys/{id}/rotate
    - GET /admin/jobs

Bootstrap keys:
- ops/bootstrap_db.py writes /data/dev_api_keys.env
  - VELU_ORG_SLUG
  - VELU_VIEWER_KEY
  - VELU_BUILDER_KEY
  - VELU_ADMIN_KEY

## Organizations

Table:
- organizations(id, name, slug, plan, created_at, updated_at)

Org routes:
- services/app_server/routes/orgs.py
  - POST /orgs/bootstrap (creates org + viewer/builder/admin keys)
  - POST /orgs (create org)
  - GET /orgs (list orgs)
  - POST /orgs/{org_id}/plan (update plan)

Scope gate:
- admin:orgs:manage required for org routes

## Jobs (Postgres)

Table:
- jobs_v2 includes:
  - org_id (NOT NULL)
  - project_id (nullable)
  - task, status, payload, result, error
  - actor_type, actor_id
  - created_by (nullable)
  - created_at, updated_at

Actor stamping:
- services/app_server/main.py
  - /tasks and /assistant-chat pass actor_type + actor_id into enqueue_job()
- services/app_server/routes/jobs.py already stamps actor_type + actor_id

Validation query:
- SELECT id, actor_type, actor_id FROM jobs_v2 ORDER BY created_at DESC LIMIT 5;

## Plan Enforcement

Plan dependency:
- services/app_server/dependencies/plan.py
  - require_plan("hero") returns 403 upgrade required if org plan rank is lower

Plan gates currently applied in services/app_server/main.py:
- app.include_router(blueprints.router, ... require_plan("hero"))
- app.include_router(assistant.router, ... require_plan("hero"))
- POST /assistant-chat has Depends(require_plan("hero"))

Verification:
- Base org key calling /assistant-chat must return 403 upgrade required
- Hero org key calling /assistant-chat must return 200 and enqueue chat job

## Local Ops Commands

Load dev keys from container:
- set -a
- source <(docker compose exec -T app sh -lc 'cat /data/dev_api_keys.env')
- set +a

Rebuild and recreate runtime after code changes:
- docker compose up -d --build --force-recreate app worker

Check plan for an org:
- docker compose exec -T postgres sh -lc '
  psql -U velu -d velu_main -c "select slug, plan from organizations where slug='\''baseorg'\'';"
  '

Confirm plan dependency file path in container:
- docker compose exec -T app sh -lc 'python - << "PY"
  import inspect
  from services.app_server.dependencies.plan import require_plan
  print(inspect.getsourcefile(require_plan))
  PY'

## Known Good Tests

1) Health
- curl -s http://127.0.0.1:8001/health | jq

2) Builder submits plan job (org-scoped)
- JOB_ID=$(curl -s -X POST http://127.0.0.1:8001/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $VELU_BUILDER_KEY" \
  -d '{"task":"plan","payload":{"idea":"hello"}}' | jq -r .job_id)

- curl -s http://127.0.0.1:8001/results/$JOB_ID \
  -H "X-API-Key: $VELU_BUILDER_KEY" | jq

3) Viewer blocked from submit
- curl -i -s -X POST http://127.0.0.1:8001/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $VELU_VIEWER_KEY" \
  -d '{"task":"plan","payload":{"idea":"nope"}}'

4) Base plan blocked from /assistant-chat
- curl -i -s -X POST http://127.0.0.1:8001/assistant-chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $BASE_BUILDER_KEY" \
  -d '{"payload":{"message":"hi"}}'
Expected: 403 {"detail":"upgrade required"}

5) Actor stamped in result
- curl -s http://127.0.0.1:8001/results/$JOB_ID \
  -H "X-API-Key: $VELU_BUILDER_KEY" | jq '.item.actor_type,.item.actor_id'
Expected: "api_key" and a uuid

## Security Defaults

- Security headers middleware enabled
- Scopes enforced only for DB-backed API keys (org_id present)
- No secret storage in repo; pepper set via env
- /orgs/bootstrap currently returns raw keys (safe for local/dev; lock down for prod)


# VELU STATE  
Last updated:  21/12/2025 at 15.00 PM

## Runtime
- docker compose services: data_init, postgres, app, worker, db_bootstrap (profile bootstrap)
- postgres backend enabled via TASK_DB_BACKEND=postgres
- org-scoped multi-tenant enforced in postgres mode

## Storage
- volumes: velu-data (/data), velu_git-data (/git), velu_workspace-data (/workspace), velu_pgdata
- postgres schema includes organizations.plan and api_keys, jobs_v2

## Auth
- api key lookup: services/app_server/auth.py
- api key hashing shared with services/app_server/models/api_key.py (VELU_API_KEY_PEPPER)
- claims include org_id, scopes, actor_type, actor_id when DB-backed key matches
- scope enforcement: services/app_server/dependencies/scopes.py
- plan enforcement: services/app_server/dependencies/plan.py

## Job queue
- enqueue + storage: services/queue/jobs_sqlite.py
- postgres table: jobs_v2
- worker: services/queue/worker_entry.py
- workspace isolation by org_id/job_id under WORKSPACE_BASE or /workspace

## Actor stamping
- /tasks and /assistant-chat pass actor_type and actor_id into enqueue_job
- /results includes actor_type and actor_id in response
- jobs_v2 rows store actor_type and actor_id

## Admin routes
- admin router: services/app_server/admin.py
- requires postgres backend and admin scopes
- api key management: services/auth/api_keys.py

## Orgs routes
- orgs router: services/app_server/routes/orgs.py
- endpoints:
  - POST /orgs/bootstrap (creates org + viewer/builder/admin keys)
  - POST /orgs
  - GET /orgs
  - POST /orgs/{org_id}/plan
- protected by scope admin:orgs:manage

## Plan tiers feature map
base
- allowed: GET /health, GET /ready, GET /auth/mode
- allowed: GET /results/{job_id} with jobs:read
- blocked: POST /tasks (upgrade required)
- blocked: POST /assistant-chat (upgrade required)

hero
- allowed: base features
- allowed: POST /tasks with jobs:submit
- allowed: POST /assistant-chat with jobs:submit
- allowed: blueprints router
- allowed: assistant router

superhero
- reserved for future high-cost/high-risk tasks and features
- candidates: execute, deploy, advanced integrations, higher limits

## Keys
- keys stored hashed in api_keys.hashed_key
- raw keys returned only on create/rotate/bootstrap and must be treated as secrets
- recommended: do not return raw keys in non-local environments
