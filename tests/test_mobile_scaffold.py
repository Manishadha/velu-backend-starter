from __future__ import annotations

from services.agents import mobile_scaffold


def test_mobile_scaffold_react_native() -> None:
    payload = {
        "blueprint": {
            "id": "demo_mobile",
            "name": "Demo Mobile",
            "kind": "mobile_app",
            "frontend": {
                "framework": "react_native",
                "language": "typescript",
                "targets": ["android", "ios"],
            },
        }
    }
    result = mobile_scaffold.handle(payload)
    assert result["ok"] is True

    files = result.get("files") or []
    paths = {f["path"] for f in files}

    assert "mobile/react_native/App.tsx" in paths
    assert "mobile/react_native/app.json" in paths
    assert "mobile/react_native/package.json" in paths

    pkg = next(f for f in files if f["path"] == "mobile/react_native/package.json")
    content = pkg["content"]
    assert '"expo"' in content
    assert '"react-native"' in content


def test_mobile_scaffold_flutter() -> None:
    payload = {
        "blueprint": {
            "id": "demo_flutter",
            "name": "Demo Flutter",
            "kind": "mobile_app",
            "frontend": {
                "framework": "flutter",
                "language": "dart",
                "targets": ["android", "ios"],
            },
        }
    }
    result = mobile_scaffold.handle(payload)
    assert result["ok"] is True

    files = result.get("files") or []
    paths = {f["path"] for f in files}

    assert "mobile/flutter/pubspec.yaml" in paths
    assert "mobile/flutter/lib/main.dart" in paths

    pubspec = next(f for f in files if f["path"] == "mobile/flutter/pubspec.yaml")
    content = pubspec["content"]
    assert "flutter:" in content
    assert "sdk: flutter" in content
