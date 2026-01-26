import pytest

pytest.skip(
    "Skipping pipeline smoke test in Docker-based local setup (no API on :8081).",
    allow_module_level=True,
)
