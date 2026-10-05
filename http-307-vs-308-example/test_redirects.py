"""Tests for the 308 on /v1/orders: the redirect itself, then the followed request."""
from fastapi.testclient import TestClient

from app import app

ORDER = {"sku": "BOOK-42", "qty": 2}


def test_v1_orders_is_a_permanent_redirect():
    client = TestClient(app, follow_redirects=False)
    response = client.post("/v1/orders", json=ORDER)
    assert response.status_code == 308
    assert response.headers["Location"] == "/v2/orders"
    assert response.headers["Cache-Control"] == "max-age=3600"


def test_followed_redirect_keeps_method_and_body():
    client = TestClient(app, follow_redirects=True)
    response = client.post("/v1/orders", json=ORDER)
    assert response.status_code == 201
    assert response.json()["sku"] == "BOOK-42"
    assert response.headers["Location"].startswith("/v2/orders/")
