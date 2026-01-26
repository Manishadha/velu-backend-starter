import os
import uuid

import pytest
from fastapi.testclient import TestClient

from services.app_server.main import create_app


def make_client():
    return TestClient(create_app())


@pytest.mark.parametrize(
    "env_value, override_raw, expect_raw",
    [
        ("local", None, True),
        ("test", None, True),
        ("dev", None, True),
        ("prod", None, False),
        ("prod", "1", True),
    ],
)
def test_orgs_bootstrap_raw_key_policy(env_value, override_raw, expect_raw):
    # must enable DB lookup during pytest
    os.environ["VELU_TEST_DB_LOOKUP"] = "1"

    os.environ["ENV"] = env_value
    if override_raw is None:
        os.environ.pop("ORG_BOOTSTRAP_RETURN_RAW", None)
    else:
        os.environ["ORG_BOOTSTRAP_RETURN_RAW"] = override_raw

    platform_key = os.getenv("TEST_PLATFORM_ADMIN_KEY")
    assert platform_key, "TEST_PLATFORM_ADMIN_KEY must be set"

    client = make_client()

    slug = f"pytest-{env_value}-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/orgs/bootstrap",
        headers={"X-API-Key": platform_key},
        json={"name": "Pytest Org", "slug": slug, "plan": "hero"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    viewer = body["keys"]["viewer"]

    if expect_raw:
        assert "raw_key" in viewer and viewer["raw_key"]
    else:
        assert "raw_key" not in viewer
        assert "masked_key" in viewer and viewer["masked_key"]
