# Velu Security Model (Console + API)

## Overview
Velu uses API keys (optional in local/open mode) with two layers of authorization:

1) **API Key Authentication**
- Enabled when `API_KEYS` is set.
- Key is sent via `X-API-Key` header (preferred) or `Authorization: Bearer <key>`.

2) **Authorization**
- **Roles** (RBAC) — controlled by `ENFORCE_ROLES=1`
- **Tiers** (feature gates) — controlled by `ENFORCE_TIERS=1`
- Tasks are limited by a per-task minimum role policy.

This is designed to be:
- **Open by default** in local/test (so pytest passes)
- **Enforceable** in tiers mode for real console/client testing

---

## Roles
Role rank order:
- `viewer` < `builder` < `admin`

Unknown legacy labels (alpha/beta/dev/ops) are treated as admin-equivalent for compatibility.

Used for:
- Protecting routes (routers have dependencies like `require_role("viewer")`)
- Protecting tasks (via per-task `TASK_POLICY_MIN_ROLE`)

---

## Tiers
Tier rank order:
- `base` < `hero` < `superhero`

Used for:
- “Product tier” gating (optional enforcement via `ENFORCE_TIERS=1`)

---

## Task Policy (Least Privilege)
Minimum role required per task (example):
- `plan`, `chat` → `viewer`
- `ui_scaffold`, `packager` → `builder`
- `deploy` → `admin`

Unknown tasks default to `builder` (safe default).

---

## Rate Limiting
Enabled when:
- `RATE_REQUESTS` and `RATE_WINDOW_SEC` are set.

Behavior:
- Always rate limits **by key-id bucket** (never logs full key).
- Optionally also rate limits **by client IP** if:
  - `RATE_LIMIT_BY_IP=1`

This reduces abuse (key sharing, brute forcing, flooding).

---

## Payload Limits
Optional request size protection:
- `MAX_REQUEST_BYTES` (applies to POST `/tasks` and `/assistant-chat`)

Prevents large request-body abuse.

---

## Key Revocation / Disabled Keys
You can revoke a key without removing it from `API_KEYS` by listing it in:
- `DISABLED_API_KEYS="k_bad1,k_bad2"`

Revoked keys fail auth.

---

## Minimum Key Length (Production Safety)
In non-local envs, keys must meet minimum length:
- default min is enforced outside `ENV=local|test`
- or override with: `MIN_API_KEY_LEN=32`

This prevents short/guessable keys.

---

## Audit Logging
Enable with:
- `AUDIT_LOG=/path/to/audit.jsonl`

Each request writes JSON lines:
- includes timestamp, route, status, role/tier, safe key-id
- never logs the full API key

Optionally include IP in audit logs with:
- `AUDIT_LOG_INCLUDE_IP=1`

---

## CORS
CORS origins come from:
- `CORS_ORIGINS="http://127.0.0.1:5178,http://localhost:5178"`

Local/test defaults can be permissive to avoid breaking pytest/dev.

Production guidance:
- Never use `*` with credentials in production
- Only allow your known console domains

---

## HTTPS (Production Guidance)
In production:
- use HTTPS only
- keys over HTTP are theftable

---

## Recommended Operational Hardening
- Generate long random keys (32+ bytes)
- Rotate keys periodically
- Keep audit logs
- Use rate limits (key + IP)
- Tighten CORS to only known console origins
- Consider moving to HttpOnly session cookies for real users later



---------------------------------------------------------------------------------------------------------------------

# Velu Security Model (current)

This document describes the security controls implemented in the Velu API + Velu Console.

## Roles & Tiers

We use API keys with role/tier claims.

- **Base**  → `viewer`
- **Hero**  → `builder`
- **Superhero** → `admin`

The API enforces access using:
- `ENFORCE_ROLES=1` (RBAC on routes + tasks)
- optional `ENFORCE_TIERS=1` (if you enable tier gating separately)

> In local/dev, you can run with enforcement off (open mode) for convenience and for pytest compatibility.

## Task Permissions (matches server policy)

Policy source:
- `TASK_POLICY_MIN_ROLE` for explicit overrides
- otherwise `DEFAULT_TASK_MIN_ROLE="builder"` (Hero+)

### Allowed tasks in this build

Base can run: `plan`, `chat`

Hero and Superhero can run:
`aggregate, ai_features, api_design, architecture, autodev, backend_scaffold, codegen, datamodel, execute, gitcommit, hospital_apply_patches, hospital_codegen, intake, packager, pipeline, report, requirements, security_hardening, test, testgen, ui_scaffold`

## Abuse Prevention Controls (practical)

### 1) CORS lock-down (browser protection)
- API returns `Access-Control-Allow-Origin` only for configured console origins (via `CORS_ORIGINS`).
- In production: do NOT use `*` together with credentials.

### 2) API key authentication
- Requests must send `X-API-Key: <token>` (or Bearer token if enabled).
- Keys are parsed from `API_KEYS` env.
- Keys should be long random tokens (32+ bytes).

### 3) Least privilege
- Viewer can only do safe tasks (`plan`, `chat`).
- Builder can do build/generate/package tasks.
- Admin reserved for dangerous tasks (e.g. deploy, infra).

### 4) Rate limiting
- Rate limiting is enforced by `RATE_REQUESTS` and `RATE_WINDOW_SEC`.
- Bucket is per-key (and optionally per-IP if enabled).
- Recommended: keep per-IP limiting enabled in production.

### 5) Payload size limits
- POST request payload size can be capped using `MAX_REQUEST_BYTES` for sensitive routes.

### 6) Audit logging (recommended)
- Log: `{ts, key_id, role, tier, route, task, status}`
- Never log the full API key (only a short masked key id).

### 7) HTTPS-only in production
- API keys over HTTP can be stolen.
- Always terminate TLS in production.
-------------------------------------------------------------------------------------------------------------------

How it’s computed

If a task is listed in TASK_POLICY_MIN_ROLE, it uses that minimum role.

Otherwise it falls back to DEFAULT_TASK_MIN_ROLE = "builder" → Hero+ only.

Mapping you decided:

Base → viewer

Hero → builder

Superhero → admin

Tasks  API currently exposes

From  /tasks/allowed output:

Task	Base	Hero	Superhero	Why
plan	✅	✅	✅	explicitly viewer
chat	✅	✅	✅	explicitly viewer
ui_scaffold	❌	✅	✅	explicitly builder
packager	❌	✅	✅	explicitly builder
aggregate	❌	✅	✅	default → builder
ai_features	❌	✅	✅	default → builder
api_design	❌	✅	✅	default → builder
architecture	❌	✅	✅	default → builder
autodev	❌	✅	✅	default → builder
backend_scaffold	❌	✅	✅	default → builder
codegen	❌	✅	✅	default → builder
datamodel	❌	✅	✅	default → builder
execute	❌	✅	✅	default → builder (note: “execute” is high risk; consider moving to admin later)
gitcommit	❌	✅	✅	default → builder (consider admin later if it touches repos)
hospital_apply_patches	❌	✅	✅	default → builder (likely high risk)
hospital_codegen	❌	✅	✅	default → builder
intake	❌	✅	✅	default → builder
pipeline	❌	✅	✅	default → builder
report	❌	✅	✅	default → builder
requirements	❌	✅	✅	default → builder
security_hardening	❌	✅	✅	default → builder (arguably admin)
test	❌	✅	✅	default → builder
testgen	❌	✅	✅	default → builder

✅ So Base can only do: plan, chat
✅ Hero can do everything listed above (since everything else is builder minimum)
✅ Superhero can do everything (admin includes builder/viewer)