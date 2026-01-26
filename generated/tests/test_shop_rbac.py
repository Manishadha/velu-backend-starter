from fastapi.testclient import TestClient
from services.api.app import app


def test_public_products_list():
    with TestClient(app) as client:
        r = client.get("/api/products/")
        assert r.status_code == 200


def test_create_requires_auth():
    with TestClient(app) as client:
        r = client.post(
            "/api/products/",
            json={
                "slug": "t-noauth",
                "name": "NoAuth",
                "price": 1.0,
                "currency": "EUR",
                "in_stock": True,
                "category": "phones",
                "brand": "Test",
                "is_featured": False,
            },
        )
        assert r.status_code == 401


def test_admin_only_and_slug_unique():
    with TestClient(app) as client:
        # Login as normal user
        r = client.post(
            "/api/auth/login",
            data={"username": "user@test.com", "password": "user123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200
        user_token = r.json()["access_token"]

        r = client.post(
            "/api/products/",
            json={
                "slug": "t-user-post",
                "name": "UserPost",
                "price": 1.0,
                "currency": "EUR",
                "in_stock": True,
                "category": "phones",
                "brand": "Test",
                "is_featured": False,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 403

        # Login as admin
        r = client.post(
            "/api/auth/login",
            data={"username": "admin@test.com", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200
        admin_token = r.json()["access_token"]

        payload = {
            "slug": "t-admin",
            "name": "AdminPost",
            "price": 2.0,
            "currency": "EUR",
            "in_stock": True,
            "category": "phones",
            "brand": "Test",
            "is_featured": True,
        }

        r = client.post(
            "/api/products/", json=payload, headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 201

        r = client.post(
            "/api/products/", json=payload, headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r.status_code == 400
