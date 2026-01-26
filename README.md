

**Velu Backend Starter** is a production-style **job orchestration runtime** built with **FastAPI** and a **Postgres-backed queue** designed for **multi-worker / multi-node safety**.



## Why this project matters (what I built)
- **Atomic job claiming** using `FOR UPDATE SKIP LOCKED`
- **Leased execution** to prevent stuck jobs and enable safe re-claim after worker crash
- **Worker runtime** that executes tasks, writes results, and stores errors reliably
- **Schema + migrations** with indexes aligned to claim/reclaim queries
- **CI-ready** (tests + formatting + security scan style workflow)

> This repo is the “backend core” extracted from the larger Velu system to serve as a clean portfolio project and starter kit.

---

## Tech Stack
- **Python**, **FastAPI**, **Uvicorn**
- **PostgreSQL** (primary queue backend)
- **psycopg**
- Docker (optional)

Keywords: `distributed workers`, `queue`, `leases`, `SKIP LOCKED`, `job runner`, `idempotent-ish recovery`, `migrations`, `FastAPI backend`.

---

## Architecture (high-level)




Client
|
| POST /tasks
v
FastAPI API (services/app_server)
|
| INSERT job row (queued)
v
Postgres (jobs_v2)
^
| claim_one_job(): FOR UPDATE SKIP LOCKED + lease_expires_at
|
Worker (services/queue/worker_entry.py)
|
| run handler -> write result/error back
v
Postgres (jobs_v2.result / jobs_v2.error)


Core components:
- **API**: validates requests, enqueues jobs, exposes `/results/{job_id}`
- **DB queue**: `jobs_v2` table is the source of truth


---

## Quickstart (local demo)

### 1) Create venv + install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

2) Start Postgres (example)

If you already have Postgres running, skip this.

docker run --rm -p 5433:5432 \
  -e POSTGRES_DB=velu_main \
  -e POSTGRES_USER=velu \
  -e POSTGRES_PASSWORD=velu \
  postgres:16

3) Run migrations
export DATABASE_URL="postgresql+psycopg://velu:velu@127.0.0.1:5433/velu_main"
python -m services.db.migrate

4) Start API
export VELU_JOBS_BACKEND=postgres
uvicorn services.app_server.main:create_app --factory --port 8010

5) Start two workers (multi-worker safe)

Terminal A:

export VELU_JOBS_BACKEND=postgres
export DATABASE_URL="postgresql+psycopg://velu:velu@127.0.0.1:5433/velu_main"
export VELU_WORKER_ID=workerA
export VELU_JOB_LEASE_SEC=5
python -u -c "from services.queue.worker_entry import worker_main; worker_main()"


Terminal B:

export VELU_JOBS_BACKEND=postgres
export DATABASE_URL="postgresql+psycopg://velu:velu@127.0.0.1:5433/velu_main"
export VELU_WORKER_ID=workerB
export VELU_JOB_LEASE_SEC=5
python -u -c "from services.queue.worker_entry import worker_main; worker_main()"

6) Create a job and poll results
API="http://127.0.0.1:8010"
KEY="YOUR_API_KEY"

JOB_ID=$(curl -sS -X POST "$API/tasks" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"task":"execute","payload":{"cmd":"bash -lc \"echo start; sleep 2; echo done\""}}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['job_id'])")

echo "JOB_ID=$JOB_ID"
curl -sS "$API/results/$JOB_ID?expand=1" -H "X-API-Key: $KEY"

Multi-worker correctness (what to test)
No double execution

Run 2 workers and enqueue many jobs → each job should be claimed once.

Crash recovery via lease reclaim

set short lease: VELU_JOB_LEASE_SEC=5

kill a worker mid-work

after lease expiry, another worker should reclaim the job

Relevant code:

services/queue/jobs_postgres.py → claim_one_job(...)

migration adding lease fields: services/db/migrations/012_jobs_v2_leases.sql
Repository tour (where to look)

services/queue/jobs_postgres.py — Postgres queue backend (claim/finish/fail)

services/queue/worker_entry.py — worker loop + handler execution

services/app_server/ — FastAPI API routes

services/db/migrate.py + services/db/migrations/ — schema + migrations

Author

Mani Naduvil Sasi
Backend / Full-stack Python (FastAPI, Postgres, Docker)
GitHub: https://github.com/Manishadha
LinkedIn: https://linkedin.com/in/Manikandan (Mani) Naduvil Sasi
