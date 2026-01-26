#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate

export VELU_DATA_DIR="$PWD/.local/velu"
export TASK_DB="$PWD/.local/velu/jobs.db"
mkdir -p "$VELU_DATA_DIR"
rm -f "$TASK_DB" "$TASK_DB-wal" "$TASK_DB-shm"

# Prefer real test secret if present
if [ -f .env.test.secrets ]; then
  set -a
  . ./.env.test.secrets
  set +a
else
  export TEST_PLATFORM_ADMIN_KEY="k_super"
  export API_KEYS="k_base:viewer:base,k_hero:builder:hero,k_super:admin:superhero"
fi

pytest -q -o cache_dir=/tmp/pytest_cache
