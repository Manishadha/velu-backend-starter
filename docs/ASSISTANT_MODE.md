# Velu Assistant Mode – Chat + Builder

This document explains how to use the **Velu Assistant**:

- Talk to Velu in natural language
- Use `/assistant-chat` as a single entrypoint
- Let Velu enqueue internal tasks (`pipeline`, `repo_summary`, `hospital_codegen`, etc.)
- Inspect and download results via the same queue + artifacts

---

## 0. Processes to run

From repo root:

### Velu API (task queue + assistant endpoint)

```bash
cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export API_KEYS="dev"

uvicorn services.app_server.main:create_app --factory --port 8010

## 2. From chat to build (assistant → pipeline)

Once the assistant marks the session as `stage = "ready_to_build"`, I can type:

- `build`

The assistant enqueues a `chat` task which, in turn, enqueues a `pipeline` job.

Example:

```bash
curl -s -X POST http://127.0.0.1:8010/assistant-chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{
    "message": "build",
    "session_id": "velu_default",
    "backend": "rules"
  }' | jq

Then I look up the pipeline job:

PIPE=472  # replace with job_id from result.jobs.pipeline
curl -s "http://127.0.0.1:8010/results/$PIPE?expand=1" | jq


From there I get subjobs (requirements, architecture, ui_scaffold, etc.) and I apply
them with:

python scripts/apply_result_files.py <subjob_id>


Finally I run:

pytest -q


to ensure the repo is still green.