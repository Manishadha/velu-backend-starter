########################
# syntax=docker/dockerfile:1.7
########################

########################
# Builder
########################
FROM python:3.12-slim AS builder
WORKDIR /app


# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# hadolint ignore=DL3013,DL3042
RUN pip install --upgrade pip \
 && pip wheel --wheel-dir /wheels -r requirements.txt


########################
# Runtime base
########################
FROM python:3.12-slim AS runtime


# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl ca-certificates tini git \
 && rm -rf /var/lib/apt/lists/*

# IMPORTANT: tini installs to /usr/bin/tini
ENTRYPOINT ["/usr/bin/tini", "--"]

RUN useradd -u 10001 -m app
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

COPY --from=builder /wheels /wheels



# hadolint ignore=DL3013,DL3042
RUN pip install --upgrade pip \
 && pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

COPY --chown=app:app . .

USER app
EXPOSE 8000


########################
# API
########################
FROM runtime AS app
CMD ["uvicorn","services.app_server.main:create_app","--factory","--host","0.0.0.0","--port","8000"]


########################
# Worker
########################
FROM runtime AS worker
CMD ["python","-m","services.worker.main"]
