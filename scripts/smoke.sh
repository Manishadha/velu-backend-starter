#!/usr/bin/env bash
set -euo pipefail

API="${API:-127.0.0.1:8010}"
KEY="${API_KEY:-${KEY:-dev}}"

# repo root (best effort)
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
if command -v git >/dev/null 2>&1; then
  git_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "${git_root:-}" ]]; then
    REPO_ROOT="$git_root"
  fi
fi

hdrs=(-H 'Content-Type: application/json' -H "X-API-Key: $KEY")

post_task () {
  local body="$1"
  curl -sS -X POST "http://$API/tasks" "${hdrs[@]}" -d "$body" | jq -r .job_id
}

get_result () {
  local jid="$1"
  curl -sS "http://$API/results/$jid" "${hdrs[@]}"
}

poll_done () {
  local jid="$1"
  echo "== polling $jid =="
  for i in {1..60}; do
    out="$(get_result "$jid")"
    st="$(jq -r '.item.status' <<<"$out")"
    if [[ "$st" == "done" || "$st" == "error" ]]; then
      echo "$out" | jq '.item | {id,status,task,result,last_error}'
      return 0
    fi
    sleep 0.2
  done
  echo "timeout waiting for job $jid" >&2
  return 1
}

echo "== allowed tasks =="
curl -sS "http://$API/tasks/allowed" "${hdrs[@]}" | jq

# ------------------------------------------------------------
# 1) Pipeline (spawns execute + test) => poll all three
# ------------------------------------------------------------
jid_pipeline="$(post_task '{"task":"pipeline","payload":{"idea":"hello","module":"hello_mod"}}')"
echo "pipeline=$jid_pipeline"

pipe_out="$(get_result "$jid_pipeline")"
# wait pipeline done
for i in {1..60}; do
  pipe_out="$(get_result "$jid_pipeline")"
  st="$(jq -r '.item.status' <<<"$pipe_out")"
  [[ "$st" == "done" || "$st" == "error" ]] && break
  sleep 0.2
done

echo "== pipeline result =="
echo "$pipe_out" | jq '.item | {id,status,task,result,last_error}'

ex="$(jq -r '.item.result.subjobs.execute // empty' <<<"$pipe_out")"
te="$(jq -r '.item.result.subjobs.test // empty' <<<"$pipe_out")"

if [[ -n "${ex:-}" ]]; then
  poll_done "$ex"
else
  echo "pipeline did not return subjobs.execute" >&2
  exit 1
fi

if [[ -n "${te:-}" ]]; then
  poll_done "$te"
else
  echo "pipeline did not return subjobs.test" >&2
  exit 1
fi

# ------------------------------------------------------------
# 2) Plan -> codegen -> execute(files) -> test -> report
#    Force shared repo dir so execute+test can see the same files.
# ------------------------------------------------------------
jid_plan="$(post_task '{"task":"plan","payload":{"idea":"hello","module":"hello_mod"}}')"
echo "plan=$jid_plan"
poll_done "$jid_plan"

jid_codegen="$(post_task '{"task":"codegen","payload":{"idea":"hello","module":"hello_mod"}}')"
echo "codegen=$jid_codegen"
poll_done "$jid_codegen"

files_json="$(get_result "$jid_codegen" | jq -c '.item.result.files')"

jid_exec="$(
  curl -sS -X POST "http://$API/tasks" "${hdrs[@]}" \
    -d "$(jq -c --argjson files "$files_json" --arg root "$REPO_ROOT" \
          '{task:"execute", payload:{target_dir:$root, files:$files}}')" \
  | jq -r .job_id
)"
echo "execute=$jid_exec"
poll_done "$jid_exec"

jid_test="$(post_task "$(jq -c --arg root "$REPO_ROOT" \
  '{task:"test",payload:{rootdir:$root,tests_path:"tests/test_hello_mod.py",args:["-q","--maxfail=1","--disable-warnings"]}}'
)")"
echo "test=$jid_test"
poll_done "$jid_test"

jid_report="$(post_task "$(jq -c --argjson parent "$jid_exec" \
  '{task:"report",payload:{parent_job:$parent}}'
)")"
echo "report=$jid_report"
poll_done "$jid_report"
