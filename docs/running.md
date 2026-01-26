Velu – Local Development & Architecture Summary

This document explains how to run Velu locally, what components exist, what security is implemented, and how the API + Console + Worker interact.

1. High-level architecture

Velu has three main runtime components:

┌────────────┐        ┌──────────────┐        ┌──────────────┐
│  Frontend  │ ─────▶ │   Velu API   │ ─────▶ │   Worker     │
│  Console   │        │   (8010)     │        │  (agents)   │
│  (Vite)    │        │              │        │              │
└────────────┘        └──────────────┘        └──────────────┘
        ▲                       │
        │                       ▼
        │                SQLite job DB
        │
        ▼
Client (browser)

2. Components & ports
Component	Purpose	Port
Velu API	Auth, rate-limit, task orchestration	8010
Velu Worker	Executes tasks (agents, codegen, etc.)	—
Velu Console UI	Web UI (queue, assistant, i18n, etc.)	5178
3. Running Velu locally
3.1 Python environment
cd ~/Downloads/velu
source .venv/bin/activate

3.2 Start the worker

The worker executes all tasks (plan, codegen, pipeline, etc.).

cd ~/Downloads/velu
source .venv/bin/activate

export VELU_ENABLE_PACKAGER=1
python -m services.worker.main


Notes:

No network port

Can be restarted independently

Safe to run before or after the API

3.3 Start the API (port 8010)
Open mode (no tiers, no roles)
cd ~/Downloads/velu
source .venv/bin/activate

unset API_KEYS
unset ENFORCE_ROLES
unset ENFORCE_TIERS

export TASK_DB="$PWD/data/jobs.db"

uvicorn services.app_server.main:create_app --factory --port 8010

Keyed / tiered mode (optional)
export API_KEYS="dev_builder:builder,dev_hero:hero"
export ENFORCE_ROLES=1
export ENFORCE_TIERS=1


Then start the API as above.

4. Velu Console (frontend UI)
4.1 Install & run
cd velu-console
npm install

# Open mode
npm run dev:open

# OR tier-aware mode
npm run dev:tiers


Default URL:

http://127.0.0.1:5178


The console:

Talks directly to http://127.0.0.1:8010

Sends X-API-Key when provided

Adapts UI based on /tasks/allowed

5. Authentication & security (what is implemented)
5.1 API keys

API keys are long-lived tokens

Passed via X-API-Key header

Never logged in full (only key_id prefixes)

5.2 Rate limiting

Applied before task execution:

Per API key bucket

Per IP bucket

Configurable via:

RATE_REQUESTS

RATE_WINDOW_SEC

This prevents:

Key abuse

IP-based flooding

Shared-key amplification

5.3 Roles & tiers (optional)

Velu supports logical tiers, not billing tiers:

base

hero

superhero

Enforcement is server-side only.
The console only reflects what /tasks/allowed says.

5.4 Task allow-listing

The API exposes:

GET /tasks/allowed


Example response:

{
  "ok": true,
  "tasks": [
    "plan",
    "codegen",
    "pipeline",
    "intake",
    "autodev",
    "packager",
    ...
  ]
}


Important:

If a task is not listed, it is NOT supported

The console disables it automatically

repo_summary is intentionally not implemented

6. About repo_summary (important)

repo_summary does not exist in the worker

It does not appear in /tasks/allowed

Therefore:

Console shows it as “not allowed”

This is correct behavior

Changing API keys will not enable it

To enable it, a worker handler must be written.
Until then, it remains UI-disabled by design.

7. Assistant (chat-driven builder)

Velu includes an Assistant API:

Endpoint: /assistant-chat

Modes:

rules

local_llm

remote_llm

Console provides:

Session-based chat

Multi-step planning

Build trigger (build)

Automatic job polling

This is how clients can generate projects without touching the queue UI.

8. Artifacts & ZIP downloads

When tasks like packager run:

Worker produces a ZIP artifact

API exposes it under:

GET /artifacts/{filename}


Console shows a Download ZIP button

Client can:

Download

Unzip

Run tests locally

This is the handoff point for clients.

9. Database (current state)

SQLite only

Stores:

Jobs

Status

Payloads

No users table

No admin UI

No billing DB

This is intentional at this stage.

Admin is currently:

Environment variables

API key management

Server operator responsibility

10. Current status (summary)

✅ API security wired
✅ Rate limiting working
✅ Console adapts to backend truth
✅ Assistant fully functional
✅ Worker isolated and stable
✅ ZIP artifact delivery works

🚫 No admin panel (by design)
🚫 No repo_summary task
🚫 No user database

11. Recommended next steps (future work)

Add real repo_summary worker handler (optional)

Add persistent API key storage (DB)

Add admin-only endpoints

Add OAuth / session-based auth (instead of raw keys)

Add production deployment configs

“This is my current Velu setup. Help me with next steps.”