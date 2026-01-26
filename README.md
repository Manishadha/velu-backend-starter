

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




