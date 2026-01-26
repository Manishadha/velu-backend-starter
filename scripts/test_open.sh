#!/usr/bin/env bash
set -euo pipefail
unset DATABASE_URL TASK_DB_BACKEND API_KEYS ENFORCE_ROLES ENFORCE_TIERS RATE_LIMIT_BY_IP
pytest -q --strict-markers
