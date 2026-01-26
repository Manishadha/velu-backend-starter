# Velu – Running & Usage Guide

This file documents how to run **Velu API + Worker + Velu Console**, what each console tab does, and sample prompts you can use as a “client” to test end‑to‑end generation.

---

## 1) (status)

✅ **Velu API** (FastAPI) running on **port 8010**  
✅ **Velu worker** running and processing queue jobs  
✅ **Velu Console** (Vite/React) running on **port 5178**  
✅ **Assistant flow** works (Assistant tab)  
✅ **Queue flow** works (Queue tab – submit tasks + watch results)  
✅ **repo_summary task** wired end‑to‑end:
- visible in UI
- runnable from Queue tab
- runnable from API directly
- unit + integration tests pass (pytest green)

✅ **Tiers & Open modes** supported via separate console env files  
✅ **Packaging** supported: the worker can produce a ZIP artifact and the console shows a download button when a packager job completes.

---

## 2) Ports & URLs

### Local ports
- **Velu API:** `http://127.0.0.1:8010`
- **Velu Console:** `http://127.0.0.1:5178`

### Useful endpoints
- Health: `GET /health`
- Allowed tasks: `GET /tasks/allowed`
- Enqueue task: `POST /tasks`
- Watch result: `GET /results/{job_id}?expand=1`
- Recent jobs: `GET /tasks/recent`
- Artifacts download: `GET /artifacts/{filename}`
- Assistant: `POST /assistant-chat`

### i18n endpoints
- Locales: `GET /v1/i18n/locales`
- Messages preview: `GET /v1/i18n/messages?locale=xx`
- Generate product messages: `POST /v1/i18n/messages`
- Translate: `POST /v1/i18n/translate`

---

## 3) How to run (Worker + API + Console)

### 3.1 Activate venv
```bash
cd ~/Downloads/velu
source .venv/bin/activate
```

### 3.2 Run the worker
Worker processes queued jobs (pipeline, plan, repo_summary, packager, etc.)

```bash
export VELU_ENABLE_PACKAGER=1
python -m services.worker.main
```

### 3.3 Run the API (port 8010)
The API uses SQLite DB at `$TASK_DB` (defaults to `./data/jobs.db` if not set).

```bash
export TASK_DB="$PWD/data/jobs.db"
# optional, see Security section:
# export API_KEYS="dev"

uvicorn services.app_server.main:create_app --factory --port 8010
```

### 3.4 Run the console (port 5178)
```bash
cd velu-console
npm install

# “Open mode” console
npm run dev:open

# “Tiers mode” console
npm run dev:tiers
```

---

## 4) Console environment files (Open vs Tiers)

created **two env files** inside `velu-console` (one for open mode, one for tiers mode).  
The console reads:

- `VITE_VELU_API_BASE_URL` (or fallback `VITE_API_URL`)
- `VITE_VELU_API_KEY` (optional; can also be set in UI, stored in localStorage)

### Open mode
- API may accept requests without strict role/tier enforcement (depends on API env flags).
- Useful for local dev and debugging.

### Tiers mode
- API key is normally required.
- The console shows plan tier labels (Base/Hero/Superhero UI labels), but the backend canonical tiers are:
  - `starter`
  - `pro`
  - `enterprise`

> The UI labels can be “Base/Hero/Superhero”, while the API internally uses `starter/pro/enterprise`.

---

## 5) Tabs & features inside Velu Console

### 5.1 Queue tab (Velu queue)
What it does:
- Lets you submit tasks to `/tasks`
- Watches a job via `/results/{id}?expand=1`
- Shows “Recent” jobs and lets you watch them
- Provides **Repo insight** (repo_summary)
- Provides **Autodev** runner (autodev agent)

#### Quick Start Wizard (Queue → Quick Start)
- Builds a structured intake payload (kind, idea, frontend, backend, db, module, schema, languages)
- Submits `intake` task to the worker

Use it when you want “guided” pipeline runs.

#### Manual submit (Queue → Quick Start → Submit manual)
- Lets you enqueue one of the selected tasks by name (plan/codegen/pipeline/intake/repo_summary/packager/autodev).
- Useful for debugging and verifying tiers/permissions.

#### Repo insight (Queue → Repo insight)
Runs `repo_summary` on a repo root. It returns:
- `stats.total_files_seen`
- file counts by extension
- top directories
- optional focus directory counts
- `languages` (language detection by extension)
- optional safe `snippets` sampling (off by default)

#### Autodev (Queue → Autodev)
Runs the `autodev` task:
- cycles through improvement steps
- can run tests
- returns results and patches (depends on your autodev agent behavior)

---

### 5.2 Assistant tab
What it does:
- Talks to `POST /assistant-chat`
- Maintains a session (`session_id`) stored server-side in `data/chat_sessions/*.json`
- Walks the user through: product type → goal → features → pages → target users → design style → module name
- When you type **build**, it enqueues:
  - `intake` job
  - optionally `packager` job (if `VELU_ENABLE_PACKAGER=1`)

Backend selector (in UI):
- Rules: deterministic assistant
- Local LLM: same flow right now (unless you wire a local model)
- Remote LLM: rewrites the “rules” output for nicer text (if configured)

---

### 5.3 Help tab
What it does:
- Shows the “how to run” commands
- Shows ports and typical run steps

---

### 5.4 Languages (i18n) tab
What it does:
- Shows locales supported by the server
- Lets you preview locale messages
- Generates “product messages” for multiple locales
- Performs quick translation

Use it when the client wants multi-language UI text.

---

## 6) repo_summary task – what it does (safe)

Task name: **`repo_summary`**

**Purpose**
- Gives a safe overview of a repo: file counts, extensions, top directories, language estimate, and (optionally) small safe excerpts.

**Safety defaults**
- Snippets are **OFF** by default.
- When snippets are enabled, the agent applies:
  - maximum files
  - maximum bytes per file
  - maximum total bytes
  - optional redaction

**Example API call**
```bash
curl -s http://127.0.0.1:8010/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{
    "task": "repo_summary",
    "payload": {
      "root": ".",
      "focus_dirs": ["services", "tests"],
      "include_snippets": false
    }
  }' | jq
```

---

## 7) Packaging – how the client gets a ZIP

If `VELU_ENABLE_PACKAGER=1`:
- Assistant “Build now” / “build” command triggers a `packager` job after `intake`
- Queue tab shows completed packager results with an **artifact_path**
- The UI exposes a **Download ZIP** button that links to:
  - `GET /artifacts/{filename}`

Typical client test flow:
1) Run the assistant build (Assistant tab)
2) Wait for intake + packager to finish in Queue tab
3) Download ZIP from the packager result
4) Unzip and run the generated project locally (instructions are included inside the package)

---

## 8) Security and controls (what we added / supported)

### API keys
- API supports `X-API-Key`
- Keys can be supplied via env `API_KEYS="dev,..."` (depending on your app config)
- Console stores key in localStorage and attaches it to all requests

### Optional enforcement flags
used these during tests (unsetting them makes tests easier):
- `API_KEYS`
- `ENFORCE_ROLES`
- `ENFORCE_TIERS`
- `RATE_LIMIT_BY_IP`

### Safe repo_summary behavior
- Snippets off by default
- Optional redaction patterns for common secrets/tokens
- Excluded dirs are ignored (like `.git`, `node_modules` etc. — your repo_summary agent enforces this)

### Hardened posture (assistant spec)
Assistant can mark:
- `security_posture: standard | hardened`
This is used to influence:
- plan tier (starter/pro/enterprise)
- defaults (e.g., enterprise tends toward postgres vs sqlite)

---

## 9) Sample “client” prompt texts (copy/paste)

These are good texts to paste into **Assistant tab** to simulate real client requests.

### 9.1 Simple website (company landing)
> I want a simple website for my company. Goal: present services, show portfolio, contact form. Pages: Home, Services, Portfolio, About, Contact. Style: clean and minimal. Languages: English, French, Dutch. Project name: acme_site.

### 9.2 E‑commerce store
> I want an e-commerce website to sell shoes online. Features: product catalog, search, cart, checkout, payments, order history, admin to manage products. Pages: Home, Shop, Product, Cart, Checkout, Orders, Admin. Style: modern and bold. Use Next.js + FastAPI. Database: Postgres. Languages: English, French. Project name: shoe_store.

### 9.3 SaaS / multi-tenant dashboard (architect + hardened)
> We need a multi-tenant SaaS dashboard for B2B clients. Must support SSO, audit logs, IP allowlist, roles (Admin, Manager, Staff), billing plans. Pages: Dashboard, Users, Billing, Settings, Audit Logs. Style: professional and clean. Project name: tenant_portal.

### 9.4 Internal admin dashboard
> Build an internal dashboard for our team to track KPIs, reports, and user management. Features: login, roles, analytics, exports. Pages: Dashboard, Reports, Users, Settings. Style: dark mode. Project name: ops_dashboard.

### 9.5 API-only backend
> I only need a backend API for managing customers and orders. CRUD endpoints, auth, and tests. No frontend. Database: Postgres. Project name: orders_api.

### 9.6 Mobile app concept
> I want a mobile app for booking appointments. Features: user login, calendar booking, reminders, admin to manage slots. Style: simple and friendly. Project name: book_easy.

---

## 10) How to test end-to-end (quick checklist)

### API is alive
```bash
curl -s http://127.0.0.1:8010/health | jq
```

### Worker is alive
- You should see worker logs: “worker: online …” and “worker: done …” as jobs complete.

### Allowed tasks
```bash
curl -s http://127.0.0.1:8010/tasks/allowed | jq
```

### Console flows
- Queue tab: submit `plan` or `repo_summary` → watch result → ensure status becomes `done`
- Assistant tab: run a prompt → answer questions → type `build` → watch intake job and (optionally) packager job

---

