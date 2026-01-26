from __future__ import annotations

import zipfile
from pathlib import Path

from services.agents import packager


def test_packager_includes_mobile_directory(tmp_path) -> None:
    base = tmp_path
    mobile_dir = base / "mobile" / "react_native"
    mobile_dir.mkdir(parents=True, exist_ok=True)

    app_file = mobile_dir / "App.tsx"
    app_file.write_text("// mobile app", encoding="utf-8")

    (base / "src").mkdir()
    (base / "requirements.txt").write_text("", encoding="utf-8")

    artifacts_dir = base / "artifacts"
    from services.agents import packager as packager_module

    packager_module.BASE_DIR = base
    packager_module.ARTIFACTS_DIR = artifacts_dir

    res = packager.handle({"module": "mobile_demo"})
    assert res["ok"] is True

    zip_path = Path(res["artifact_path"])
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())

    assert "mobile/react_native/App.tsx" in names
