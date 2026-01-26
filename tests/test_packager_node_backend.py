from __future__ import annotations

from pathlib import Path
import zipfile

from services.agents import packager


def test_packager_includes_node_backend(tmp_path: Path) -> None:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    module = "react_ml_demo"
    result = packager.handle({"module": module})

    assert result["ok"] is True
    zip_path = Path(result["artifact_path"])
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())

    assert "generated/services/node/app.js" in names
    assert "generated/services/node/package.json" in names
