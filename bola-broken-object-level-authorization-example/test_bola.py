"""Two-user authorization tests: Bob must not reach any of Alice's orders or addresses.

Run against the secure app (default) or the vulnerable one: APP=vulnerable_app pytest -q
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

ALICE = {"Authorization": "Bearer demo-token-alice"}  # fake demo tokens
BOB = {"Authorization": "Bearer demo-token-bob"}
SAM = {"Authorization": "Bearer demo-token-sam"}
ALICE_ORDER, ALICE_ADDRESS, BOB_ADDRESS = 1001, 11, 12


@pytest.fixture
def client():
    module = importlib.reload(importlib.import_module(os.environ.get("APP", "secure_app")))
    return TestClient(module.app)


# Every route that takes an order ID, called by Bob with Alice's order
BOB_ON_ALICES_ORDER = [
    ("GET", f"/orders/{ALICE_ORDER}", None),
    ("PATCH", f"/orders/{ALICE_ORDER}", {"address_id": BOB_ADDRESS}),
    ("DELETE", f"/orders/{ALICE_ORDER}", None),
]


@pytest.mark.parametrize("method,path,body", BOB_ON_ALICES_ORDER, ids=["GET", "PATCH", "DELETE"])
def test_other_customer_gets_404(client, method, path, body):
    assert client.request(method, path, json=body, headers=BOB).status_code == 404


@pytest.mark.parametrize("method,path,body", BOB_ON_ALICES_ORDER, ids=["GET", "PATCH", "DELETE"])
def test_owner_still_allowed(client, method, path, body):
    if body:
        body = {"address_id": ALICE_ADDRESS}
    assert client.request(method, path, json=body, headers=ALICE).status_code in (200, 204)


def test_list_ignores_customer_id_parameter(client):
    orders = client.get("/orders?customer_id=1", headers=BOB).json()
    assert all(o["customer_id"] == 2 for o in orders)


def test_body_cannot_reference_another_customers_address(client):
    r = client.post("/orders", json={"book": "Emma", "total": 9.99, "address_id": ALICE_ADDRESS},
                    headers=BOB)
    assert r.status_code == 422


def test_support_can_read_but_not_cancel(client):
    assert client.get(f"/orders/{ALICE_ORDER}", headers=SAM).status_code == 200
    assert client.delete(f"/orders/{ALICE_ORDER}", headers=SAM).status_code == 404
