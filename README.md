# Velu Backend Starter

Production-style **job orchestration backend** built with **FastAPI + PostgreSQL**, designed for **multi-worker / multi-node safe execution**.

This project demonstrates how to build a **reliable distributed job runner** with:

- atomic job claiming
- lease-based execution
- crash recovery
- safe re-claim after worker failure
- clean migrations
- API + worker separation

It is extracted from the larger **Velu system** as a focused, portfolio-ready backend core.

---

##  Why this project matters

This is **not just a queue**.

It solves real production problems:

✅ No double execution  
✅ Safe multi-worker concurrency  
✅ Worker crash does NOT lose jobs  
✅ Automatic recovery via lease expiration  
✅ Postgres as the single source of truth  
✅ Simple horizontal scaling  

These are the same patterns used by:
- distributed task systems
- CI runners
- job schedulers
- background processing platforms

---

##  Architecture (high level)

Client
|
| POST /tasks
v
FastAPI API
|
| INSERT job (queued)
v
Postgres (jobs_v2)
^
| claim_one_job() → FOR UPDATE SKIP LOCKED + lease
|
Workers (many processes)
|
| execute task
| write result / error
v
Postgres


---

## ⚙️ Core Features

### 🔹 Atomic claiming
Uses:

```sql
FOR UPDATE SKIP LOCKED
Multiple workers can safely compete without collisions.

🔹 Lease-based execution
Each job has:

claimed_by

claimed_at

lease_expires_at

If a worker dies:

lease expires

another worker automatically reclaims

No stuck jobs. No manual cleanup.

🔹 Crash recovery
Workers can be killed anytime:

kill -9 workerA
Another worker continues automatically.

🔹 Clean separation
services/app_server   → API
services/queue       → queue + worker
services/db          → migrations
🛠 Tech Stack
Python 3.12

FastAPI

PostgreSQL

psycopg

Docker (optional)

Bash tooling

Keywords:

distributed systems, workers, leasing, SKIP LOCKED, crash recovery, backend engineering, job queues

 Quickstart (local demo)
1) Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
2) Start Postgres
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
5) Start workers
Terminal A:

export VELU_WORKER_ID=workerA
python -u -c "from services.queue.worker_entry import worker_main; worker_main()"
Terminal B:

export VELU_WORKER_ID=workerB
python -u -c "from services.queue.worker_entry import worker_main; worker_main()"
6) Submit job
curl -X POST http://127.0.0.1:8010/tasks \
  -H "X-API-Key: <KEY>" \
  -H "content-type: application/json" \
  -d '{"task":"execute","payload":{"cmd":"echo hello"}}'
 Crash Recovery Demo (screenshots)
 Full walkthrough with screenshots:

docs/demos/pg-leases
Demonstrates:

job claimed by workerA

workerA crash

lease expiry

workerB reclaim

job finishes successfully

This proves:
✔ multi-worker safety
✔ leasing
✔ recovery

 What to test (interview talking points)
Run two workers and:

Test 1 — no double execution
Submit 100 jobs
→ each runs exactly once

Test 2 — crash recovery
Kill worker mid-task
→ another worker reclaims automatically

Test 3 — horizontal scale
Run 5+ workers
→ throughput increases linearly

 Repository Tour
Path	Purpose
services/queue/jobs_postgres.py	Postgres queue backend
services/queue/worker_entry.py	worker runtime
services/app_server	API routes
services/db/migrations	schema
docs/demos	screenshots
 Author
Mani Naduvil Sasi
Backend / Distributed Systems Engineer

GitHub: https://github.com/Manishadha

LinkedIn: https://linkedin.com/in/Manikandan (Mani) Naduvil Sasi

