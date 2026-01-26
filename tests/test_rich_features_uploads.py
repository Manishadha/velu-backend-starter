from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app

client = TestClient(app)


def _upload_png(name: str = "test.png", size: int = 16) -> dict:
    content = b"\x89PNG\r\n\x1a\n" + b"x" * (size - 8 if size > 8 else 0)
    files = {"file": (name, content, "image/png")}
    response = client.post("/v1/files/upload", files=files)
    assert response.status_code == 201
    return response.json()


def test_file_upload_accepts_valid_image() -> None:
    data = _upload_png()
    assert data["filename"] == "test.png"
    assert data["content_type"] == "image/png"
    assert data["size"] > 0
    assert isinstance(data["id"], int)


def test_file_upload_rejects_large_file() -> None:
    large_content = b"x" * (2 * 1024 * 1024)
    files = {"file": ("big.png", large_content, "image/png")}
    response = client.post("/v1/files/upload", files=files)
    assert response.status_code == 413
    body = response.json()
    assert body["detail"] == "file_too_large"


def test_file_upload_rejects_disallowed_type() -> None:
    files = {"file": ("malware.exe", b"dummy", "application/x-msdownload")}
    response = client.post("/v1/files/upload", files=files)
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "unsupported_media_type"


def test_media_gallery_lists_recent_uploads() -> None:
    first = _upload_png("first.png")
    second = _upload_png("second.png")

    response = client.get("/v1/media")
    assert response.status_code == 200
    items = response.json()
    ids = {item["id"] for item in items}
    assert first["id"] in ids
    assert second["id"] in ids

    for item in items:
        assert "filename" in item
        assert "content_type" in item
        assert "size" in item
        assert "id" in item
        assert "path" not in item


def test_media_item_details() -> None:
    uploaded = _upload_png("detail.png")
    item_id = uploaded["id"]

    response = client.get(f"/v1/media/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["filename"] == "detail.png"
