FROM python:3.11-slim

# Keep image small & reproducible enough; ignore DL3008 for Debian packages
# hadolint ignore=DL3008
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends \
      git ca-certificates tzdata sqlite3 \
 && rm -rf /var/lib/apt/lists/*

# Create non-root user before copying files
RUN useradd -u 10001 -m app

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code with correct ownership (faster than chown -R)
COPY --chown=app:app . .

USER app

# Let docker-compose provide `init: true`, so no tini here
CMD ["python","-c","import sys,importlib; sys.path[:0]=['/app','/app/src']; import sitecustomize; importlib.import_module('services.queue.worker_entry').main()"]
