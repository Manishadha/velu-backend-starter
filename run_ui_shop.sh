#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/blueprints/shop_fastapi_next/generated/web"
export NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
npm install
npm run dev
