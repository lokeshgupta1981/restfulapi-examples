"""Cross-tenant tests: run them on every change (pytest -q)."""
import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import pytest
from fastapi.testclient import TestClient

import app as api
from tokens import token_for

client = TestClient(api.app)
ALICE = {"Authorization": f"Bearer {token_for('alice')}"}  # tenant acme
BOB = {"Authorization": f"Bearer {token_for('bob')}"}      # tenant globex


@pytest.fixture(autouse=True)
def fresh_limits():
    api._recent.clear()


def test_list_shows_only_own_tenant():
    items = client.get("/invoices", headers=ALICE).json()["items"]
    assert [i["id"] for i in items][:2] == [1001, 1003]
    assert all(i["id"] != 1002 for i in items)


def test_other_tenants_invoice_looks_missing():
    other = client.get("/invoices/1002", headers=ALICE)
    missing = client.get("/invoices/999999", headers=ALICE)
    assert other.status_code == missing.status_code == 404
    assert other.json()["title"] == missing.json()["title"]


def test_owner_can_read_it():
    assert client.get("/invoices/1002", headers=BOB).status_code == 200


def test_body_cannot_choose_the_tenant():
    r = client.post("/invoices", headers=ALICE,
                    json={"customer": "X", "amount_cents": 1, "tenant_id": "globex"})
    assert r.status_code == 422
    created = client.post("/invoices", headers=ALICE, json={"customer": "X", "amount_cents": 1}).json()
    assert client.get(f"/invoices/{created['id']}", headers=BOB).status_code == 404


def test_tampered_token_is_rejected():
    header, payload, sig = token_for("alice").split(".")
    forged = f"{header}.{token_for('bob').split('.')[1]}.{sig}"  # bob's claims, alice's signature
    r = client.get("/invoices", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_rate_limit_is_per_tenant():
    codes = [client.get("/invoices", headers=ALICE).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]
    assert client.get("/invoices", headers=BOB).status_code == 200


def test_unsafe_route_leaks_across_tenants():
    """Documents the bug: lookup by ID alone returns another tenant's invoice."""
    r = client.get("/unsafe/invoices/1002", headers=ALICE)
    assert r.status_code == 200 and r.json()["tenant_id"] == "globex"
