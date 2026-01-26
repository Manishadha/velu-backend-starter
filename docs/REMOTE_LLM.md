# Remote LLM 

Remote LLM integration is optional and off by default. When enabled, Velu can call a remote provider (OpenAI) for:

- Assistant backend `remote_llm`
- `/v1/ai/chat`
- `/v1/ai/summarize`

## Environment variables

Core:

- `OPENAI_API_KEY` – API key for the OpenAI client.
- `VELU_REMOTE_LLM_MODEL` – optional, default model for remote backend.
- `VELU_CHAT_MODEL` – fallback model name when the remote model is not set.
- `VELU_REMOTE_LLM_PROVIDER` – optional provider name, default `openai`.
- `LLM_PROVIDER` – legacy provider for `llm_client.chat`, default `openai`.

Assistant:

- `VELU_CHAT_BACKEND` – default assistant backend: `rules` | `local_llm` | `remote_llm`.

AI demo API:

- `AI_REMOTE_ENABLED=1` – enable remote mode for `/v1/ai/chat` and `/v1/ai/summarize`.

## Run example (assistant + worker)

```bash
cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export API_KEYS="dev"

export OPENAI_API_KEY="sk-XXX"
export VELU_REMOTE_LLM_MODEL="gpt-4.1-mini"
export AI_REMOTE_ENABLED=1

uvicorn services.app_server.main:create_app --factory --port 8010


In another terminal:

cd ~/Downloads/velu
source .venv/bin/activate

export TASK_DB="$PWD/data/jobs.db"
export VELU_ENABLE_PACKAGER=1

python -m services.worker.main

Assistant remote backend (HTTP)
curl -s -X POST http://127.0.0.1:8010/assistant-chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev" \
  -d '{
    "message": "build a small product catalog website",
    "session_id": "velu_default",
    "backend": "remote_llm"
  }'

AI demo API remote chat
curl -s -X POST http://127.0.0.1:8203/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "hello from velu ai demo"}
    ],
    "backend": "remote_llm"
  }'

