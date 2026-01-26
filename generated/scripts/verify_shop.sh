#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"

echo "== Health =="
curl -sf "$API_BASE/health" >/dev/null
echo "OK"

echo "== Public list products =="
curl -sf "$API_BASE/api/products/" >/dev/null
echo "OK"

echo "== No token POST should be 401 =="
status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/api/products/" \
  -H "Content-Type: application/json" \
  -d '{"slug":"no-token","name":"No Token","price":1.0,"currency":"EUR","in_stock":true}')
test "$status" = "401" || (echo "Expected 401, got $status" && exit 1)

echo "== Login as USER then POST should be 403 =="
USER_TOKEN=$(curl -sf -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "email=user@test.com&password=user123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/api/products/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug":"user-post","name":"User Post","price":1.0,"currency":"EUR","in_stock":true}')
test "$status" = "403" || (echo "Expected 403, got $status" && exit 1)

echo "== Login as ADMIN then POST should be 201 =="
ADMIN_TOKEN=$(curl -sf -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "email=admin@test.com&password=admin123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/api/products/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug":"verify-admin","name":"Verify Admin","price":2.0,"currency":"EUR","in_stock":true}')
test "$status" = "201" || (echo "Expected 201, got $status" && exit 1)

echo "== Slug uniqueness should be 400 =="
status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/api/products/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug":"verify-admin","name":"Dup","price":2.0,"currency":"EUR","in_stock":true}')
test "$status" = "400" || (echo "Expected 400, got $status" && exit 1)

echo "ALL CHECKS PASSED ✅"
