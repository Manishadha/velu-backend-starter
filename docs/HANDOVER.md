### Packaged app pattern (example: online_travel_full)

- Velu produces an artifact zip via `packager` task.
- Zip contents are suitable for a standalone repo:
  - `generated/` (Next.js + FastAPI)
  - `src/`, `tests/`, `pyproject.toml`, `requirements.txt`
  - `Dockerfile_packaged`, `docker-compose.packaged.yml`, `README_packaged.md`
- Typical consumer flow:
  1. Create empty GitHub repo.
  2. Unzip artifact into repo root.
  3. Run `docker compose -f docker-compose.packaged.yml up` to launch.


Repo structure snapshot:
./scripts/tree_repo.sh
