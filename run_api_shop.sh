#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/blueprints/shop_fastapi_next/generated"
exec env PYTHONPATH=. python -m uvicorn services.api.app:app --reload --port 8000
