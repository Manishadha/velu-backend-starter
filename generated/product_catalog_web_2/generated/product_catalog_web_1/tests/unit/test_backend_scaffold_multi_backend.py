from __future__ import annotations

from services.agents import backend_scaffold


def paths(result) -> set[str]:
    files = result.get("files") or []
    return {f["path"] for f in files if "path" in f}


def test_backend_scaffold_fastapi_default():
    res = backend_scaffold.handle({})
    assert res["ok"] is True
    assert res["backend"] == "fastapi"
    p = paths(res)
    assert "services/api/app.py" in p
    assert "services/api/routes/health.py" in p


def test_backend_scaffold_node_express():
    res = backend_scaffold.handle({"backend": "node"})
    assert res["ok"] is True
    assert res["backend"] == "node"
    p = paths(res)
    assert "generated/services/node/app.js" in p
    assert "generated/services/node/package.json" in p
