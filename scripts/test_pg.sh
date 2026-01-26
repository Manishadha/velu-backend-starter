#!/usr/bin/env bash
set -euo pipefail
docker compose exec -T app sh -lc '
export NO_EMBEDDED_API=1
export DATABASE_URL="postgresql+psycopg://velu:velu@postgres:5432/velu_main"
export VELU_TEST_DB_LOOKUP=1
pytest -q -c /app/pytest.ini -m integration
'
