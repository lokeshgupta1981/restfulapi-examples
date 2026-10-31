"""Regression test: a client must not be able to set server-owned fields.

    pytest -q test_mass_assignment.py                   # secure app
    APP=vulnerable_app pytest -q test_mass_assignment.py  # fails on purpose
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

os.environ["DB_URL"] = "sqlite:///test.db"
app = importlib.import_module(os.environ.get("APP", "secure_app")).app
client = TestClient(app)

SERVER_OWNED = {"role": "admin", "store_credit": 500, "email_verified": True, "id": 99}


@pytest.mark.parametrize("field,value", SERVER_OWNED.items())
def test_sign_up_cannot_set_server_owned_field(field, value):
    body = {"email": f"{field}@example.com", "name": "Test", "password": "test-pass-1", field: value}
    r = client.post("/users", json=body)
    if r.status_code == 201:
        assert r.json()[field] != value, f"client set {field}"
    else:
        assert r.status_code == 422


@pytest.fixture(scope="module")
def customer_id():
    body = {"email": "customer@example.com", "name": "Customer", "password": "test-pass-1"}
    return str(client.post("/users", json=body).json()["id"])


@pytest.mark.parametrize("field,value", {**SERVER_OWNED, "id": 777}.items())
def test_update_me_cannot_set_server_owned_field(customer_id, field, value):
    r = client.patch("/users/me", headers={"X-User-Id": customer_id}, json={field: value})
    if r.status_code == 200:
        assert r.json()[field] != value, f"client set {field}"
    else:
        assert r.status_code == 422
