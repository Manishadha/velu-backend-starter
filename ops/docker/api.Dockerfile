# ops/docker/api.Dockerfile
FROM python:3.11-slim

# --- Build-time metadata (git SHA) -------------------------------------------
ARG VELU_GIT_SHA=dev


ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VELU_GIT_SHA=${VELU_GIT_SHA}

#  extra labels for traceability
LABEL org.opencontainers.image.revision="${VELU_GIT_SHA}"    

WORKDIR /app

# System deps
# hadolint ignore=DL3008
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# App deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Security: run as non-root
RUN useradd -u 10001 -m app && chown -R app:app /app
USER app

# no CMD; compose or entrypoint will set uvicorn args
