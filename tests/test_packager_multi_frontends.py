from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from services.agents import packager


def test_packager_includes_multiple_frontends(tmp_path, monkeypatch):
    base = tmp_path

    # minimal project structure
    (base / "src").mkdir()
    (base / "generated" / "web" / "pages").mkdir(parents=True)
    (base / "web" / "pages").mkdir(parents=True)
    (base / "react_spa" / "src").mkdir(parents=True)

    (base / "src" / "app.py").write_text("x = 1", encoding="utf-8")
    (base / "generated" / "web" / "pages" / "index.tsx").write_text(
        "export default function Page() { return null }",
        encoding="utf-8",
    )
    (base / "web" / "pages" / "index.tsx").write_text(
        "export default function Home() { return null }",
        encoding="utf-8",
    )
    (base / "react_spa" / "src" / "App.jsx").write_text(
        "export default function App() { return null }",
        encoding="utf-8",
    )

    (base / "requirements.txt").write_text("", encoding="utf-8")
    (base / "pyproject.toml").write_text("[project]\nname = 'demo'", encoding="utf-8")

    monkeypatch.setattr(packager, "BASE_DIR", base)
    monkeypatch.setattr(packager, "ARTIFACTS_DIR", base / "artifacts")

    result = packager.handle({"module": "demo_multi"})
    zip_path = Path(result["artifact_path"])
    assert zip_path.is_file()

    with ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert "generated/web/pages/index.tsx" in names
    assert "web/pages/index.tsx" in names
    assert "react_spa/src/App.jsx" in names
