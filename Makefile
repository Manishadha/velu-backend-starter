.PHONY: up down logs test build-images push-ghcr clean-db fmt lint release

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	pytest -q

build-images:
	docker build -f ops/docker/api.Dockerfile -t velu-api:local .
	docker build -f ops/docker/worker.Dockerfile -t velu-worker:local .

clean-db:
	rm -f .run/jobs.db .run/tasks.db

fmt:
	black .
	ruff check --fix .

lint:
	ruff check .
	black --check .

# usage: make release TAG=v0.2.0
release:
	@if [ -z "$(TAG)" ]; then echo "TAG required, e.g. make release TAG=v0.2.0"; exit 1; fi
	@git fetch --tags --force
	@if git ls-remote --exit-code --tags origin "refs/tags/$(TAG)" >/dev/null 2>&1; then \
		echo "Tag $(TAG) already exists on remote; nothing to do."; \
	else \
		if git rev-parse -q --verify "refs/tags/$(TAG)" >/dev/null; then \
			echo "Tag $(TAG) exists locally; pushing only..."; \
		else \
			git tag -a "$(TAG)" -m "Release $(TAG)"; \
		fi; \
		git push origin "refs/tags/$(TAG)"; \
	fi

build-dist:
	rm -rf dist build src/*.egg-info
	python -m build
	twine check dist/*

clean-dist:
	rm -rf dist build src/*.egg-info
