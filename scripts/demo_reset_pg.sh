#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8010}"
API="http://127.0.0.1:${API_PORT}"
PLATFORM_KEY="${PLATFORM_KEY:-dev}"
PLAN="${PLAN:-hero}"

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-velu}"
DB_PASS="${DB_PASS:-velu}"
DB_NAME="${DB_NAME:-velu_main}"

export ENV=local
export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
export VELU_JOBS_BACKEND=postgres
export API_KEYS=postgres
export VELU_ADMIN_KEY="${VELU_ADMIN_KEY:-dev}"

LOGDIR="${LOGDIR:-/tmp/velu-demo-logs}"
mkdir -p "$LOGDIR"
API_LOG="$LOGDIR/api.log"
WORKER_LOG="$LOGDIR/worker.log"
API_PID_FILE="$LOGDIR/api.pid"
WORKER_PID_FILE="$LOGDIR/worker.pid"

kill_pidfile() {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid="$(cat "$f" 2>/dev/null || true)"
    if [[ -n "${pid//[[:space:]]/}" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
      for _ in $(seq 1 30); do
        if kill -0 "$pid" >/dev/null 2>&1; then
          sleep 0.1
        else
          break
        fi
      done
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$f"
  fi
}

http_json() {
  local method="$1"
  local url="$2"
  local key="${3:-}"
  local data="${4:-}"
  local out code
  out="$(mktemp)"

  if [[ -n "$data" ]]; then
    if [[ -n "$key" ]]; then
      code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" \
        -H "content-type: application/json" -H "X-API-Key: $key" \
        "$url" -d "$data" || true)"
    else
      code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" \
        -H "content-type: application/json" \
        "$url" -d "$data" || true)"
    fi
  else
    if [[ -n "$key" ]]; then
      code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" \
        -H "X-API-Key: $key" "$url" || true)"
    else
      code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" \
        "$url" || true)"
    fi
  fi

  if [[ "$code" != "200" ]] || [[ ! -s "$out" ]]; then
    rm -f "$out"
    echo ""
    return 0
  fi
  cat "$out"
  rm -f "$out"
}

wait_health() {
  for _ in $(seq 1 120); do
    if curl -fsS "${API}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  return 1
}

wait_job_done() {
  local job_id="$1"
  local key="$2"
  for _ in $(seq 1 2000); do
    local body st
    body="$(http_json GET "${API}/results/${job_id}?expand=1" "$key")"
    if [[ -n "${body//[[:space:]]/}" ]]; then
      st="$(jq -r '.item.status // empty' <<<"$body" 2>/dev/null || true)"
      if [[ "$st" == "done" ]]; then
        echo "$body"
        return 0
      fi
    fi
    sleep 0.25
  done
  echo ""
  return 1
}

echo "[1/7] Start Postgres"
docker compose -p velu_local up -d postgres >/dev/null

echo "[2/7] Wait for Postgres"
export PGPASSWORD="$DB_PASS"
until psql "host=${DB_HOST} port=${DB_PORT} user=${DB_USER} dbname=${DB_NAME}" -c "select 1" >/dev/null 2>&1; do
  sleep 0.2
done

echo "[3/7] Migrate"
python -m services.db.migrate

echo "[4/7] Start API + Worker (PID-managed)"
kill_pidfile "$API_PID_FILE"
kill_pidfile "$WORKER_PID_FILE"

: >"$API_LOG"
: >"$WORKER_LOG"

nohup env \
  ENV=local \
  DATABASE_URL="$DATABASE_URL" \
  VELU_JOBS_BACKEND=postgres \
  API_KEYS=postgres \
  VELU_ADMIN_KEY="$VELU_ADMIN_KEY" \
  uvicorn services.app_server.main:create_app --factory --host 0.0.0.0 --port "$API_PORT" \
  >"$API_LOG" 2>&1 &
echo $! >"$API_PID_FILE"

nohup env \
  ENV=local \
  DATABASE_URL="$DATABASE_URL" \
  VELU_JOBS_BACKEND=postgres \
  API_KEYS=postgres \
  python -u -c "from services.queue.worker_entry import worker_main; worker_main()" \
  >"$WORKER_LOG" 2>&1 &
echo $! >"$WORKER_PID_FILE"

if ! wait_health; then
  echo "API not healthy"
  tail -n 200 "$API_LOG" || true
  tail -n 200 "$WORKER_LOG" || true
  exit 1
fi

echo "[5/7] Bootstrap org (platform key)"
SLUG="org-$(python - <<'PY'
import uuid; print(uuid.uuid4().hex[:8])
PY
)"

BOOT_BODY="$(http_json POST "${API}/orgs/bootstrap" "${PLATFORM_KEY}" "{\"name\":\"Local Org\",\"slug\":\"${SLUG}\",\"plan\":\"${PLAN}\"}")"
if [[ -z "${BOOT_BODY//[[:space:]]/}" ]]; then
  echo "bootstrap failed"
  tail -n 200 "$API_LOG" || true
  exit 1
fi

BUILDER_KEY="$(jq -r '.keys.builder.raw_key // empty' <<<"$BOOT_BODY" 2>/dev/null || true)"
if [[ -z "${BUILDER_KEY//[[:space:]]/}" ]]; then
  echo "bootstrap response missing builder key"
  echo "$BOOT_BODY" | head -c 1200; echo
  exit 1
fi

echo "ORG_SLUG=${SLUG}"
echo "BUILDER_KEY=${BUILDER_KEY}"

echo "[6/7] Run pipeline"
PIPE_BODY="$(http_json POST "${API}/tasks" "${BUILDER_KEY}" '{
  "task":"pipeline",
  "payload":{"idea":"postgres demo pipeline","module":"hello_mod","kind":"web_app","locales":["en","fr"]}
}')"

PID="$(jq -r '.job_id // empty' <<<"$PIPE_BODY" 2>/dev/null || true)"
if [[ -z "${PID//[[:space:]]/}" ]]; then
  echo "pipeline submit failed"
  echo "$PIPE_BODY" | head -c 1200; echo
  tail -n 200 "$API_LOG" || true
  exit 1
fi
echo "PIPELINE_JOB=${PID}"

echo "[7/7] Wait subjobs + gates + ZIP"
RES_PIPE="$(wait_job_done "$PID" "$BUILDER_KEY")"
if [[ -z "${RES_PIPE//[[:space:]]/}" ]]; then
  echo "pipeline did not finish"
  tail -n 200 "$API_LOG" || true
  exit 1
fi

SUBJOBS="$(jq -r '.item.result.subjobs // {}' <<<"$RES_PIPE" 2>/dev/null || echo "{}")"
for name in execute test packager security_scan pipeline_waiter; do
  jid="$(jq -r --arg n "$name" '.[$n] // empty' <<<"$SUBJOBS" 2>/dev/null || true)"
  if [[ -z "${jid//[[:space:]]/}" ]]; then
    continue
  fi
  RES_SUB="$(wait_job_done "$jid" "$BUILDER_KEY")"
  ok="$(jq -r '.item.result.ok // empty' <<<"$RES_SUB" 2>/dev/null || true)"
  err="$(jq -r '.item.result.error // empty' <<<"$RES_SUB" 2>/dev/null || true)"
  echo "${name} -> ok=${ok:-} ${err}"
done

WAIT_ID="$(jq -r '.item.result.subjobs.pipeline_waiter // empty' <<<"$RES_PIPE" 2>/dev/null || true)"
GATES="{}"
ZIP_PATH=""
if [[ -n "${WAIT_ID//[[:space:]]/}" ]]; then
  RES_WAIT="$(http_json GET "${API}/results/${WAIT_ID}?expand=1" "${BUILDER_KEY}")"
  GATES="$(jq -c '.item.result.gates // {}' <<<"$RES_WAIT" 2>/dev/null || echo "{}")"
  ZIP_PATH="$(jq -r '.item.result.artifact_path // empty' <<<"$RES_WAIT" 2>/dev/null || true)"
fi

if [[ -z "${ZIP_PATH//[[:space:]]/}" ]]; then
  PACKAGER_ID="$(jq -r '.item.result.subjobs.packager // empty' <<<"$RES_PIPE" 2>/dev/null || true)"
  if [[ -n "${PACKAGER_ID//[[:space:]]/}" ]]; then
    RES_PACK="$(http_json GET "${API}/results/${PACKAGER_ID}?expand=1" "${BUILDER_KEY}")"
    ZIP_PATH="$(jq -r '.item.result.artifact_path // empty' <<<"$RES_PACK" 2>/dev/null || true)"
  fi
fi

echo "GATES=${GATES}"
echo "ZIP=${ZIP_PATH}"

if [[ -n "${ZIP_PATH//[[:space:]]/}" ]]; then
  python -m zipfile -t "$ZIP_PATH" >/dev/null
  unzip -l "$ZIP_PATH" | head -n 40
fi

DEMO_ENV="$LOGDIR/demo.env"
chmod 700 "$LOGDIR" 2>/dev/null || true
cat >"$DEMO_ENV" <<EOF
API=${API}
PLATFORM_KEY=${PLATFORM_KEY}
ORG_SLUG=${SLUG}
BUILDER_KEY=${BUILDER_KEY}
PIPELINE_JOB=${PID}
WAIT_ID=${WAIT_ID}
ZIP=${ZIP_PATH}
API_LOG=${API_LOG}
WORKER_LOG=${WORKER_LOG}
EOF
chmod 600 "$DEMO_ENV" 2>/dev/null || true

echo "WROTE_ENV=${DEMO_ENV}"
echo "Run: source ${DEMO_ENV}"
echo "OK"
echo "API=${API}"
echo "API_LOG=${API_LOG}"
echo "WORKER_LOG=${WORKER_LOG}"
