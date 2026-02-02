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

## 🚀 Why this project matters

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

## 🧠 Architecture (high level)

