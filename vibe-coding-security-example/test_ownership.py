"""Checklist item 13: a test where user B tries user A's data. Runs in CI without a server.

pytest -q                          # tests secure_app (default)
APP=vulnerable_app pytest -q       # the same tests against the vulnerable version fail
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ORDERS_SECRET_KEY", "demo-only-not-a-real-key")


@pytest.fixture()
def client():
    module = importlib.reload(importlib.import_module(os.environ.get("APP", "secure_app")))  # fresh data per test
    return TestClient(module.app)


def login(client, name):
    token = client.post("/login", json={"name": name, "password": name + "-pass"}).json()["token"]
    return {"Authorization": "Bearer " + token}


def test_owner_reads_own_order(client):
    assert client.get("/orders/101", headers=login(client, "alice")).status_code == 200


def test_other_user_cannot_read_order(client):
    assert client.get("/orders/201", headers=login(client, "alice")).status_code == 404


def test_user_cannot_make_self_admin(client):
    alice = login(client, "alice")
    client.patch("/users/me", headers=alice, json={"role": "admin"})
    assert client.get("/admin/users", headers=alice).status_code == 403


def test_customer_cannot_call_admin_route(client):
    assert client.get("/admin/users", headers=login(client, "bob")).status_code == 403
