import copy

import pytest
from fastapi.testclient import TestClient

import app as api
import pdp
from data import DOCUMENTS, USERS
from matrix import CASES
from policies import MODELS, check


def as_user(name):
    return {"Authorization": f"Bearer tok-{name}"}


@pytest.fixture
def client(monkeypatch):
    def make(model):
        monkeypatch.setattr(api, "AUTHZ_MODEL", model)
        monkeypatch.setattr(api, "docs", copy.deepcopy(DOCUMENTS))
        return TestClient(api.app)
    return make


def test_hybrid_model_matches_every_wanted_decision():
    for user, action, doc_id, wanted, _ in CASES:
        assert MODELS["hybrid"](USERS[user], action, DOCUMENTS[doc_id]) == wanted


def test_rbac_ignores_the_document():
    bob = USERS["bob"]
    assert all(MODELS["rbac"](bob, "edit", d) for d in DOCUMENTS.values())


def test_rebac_explains_the_decision():
    path = check("document:launch-plan", "viewer", "user:erin")
    assert path[0] == "folder:marketing-q4#viewer@user:erin"


def test_no_token_is_401(client):
    r = client("rbac").get("/documents/launch-plan")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


@pytest.mark.parametrize("model,status", [("rbac", 200), ("abac", 404), ("rebac", 404)])
def test_bob_edits_launch_plan(client, model, status):
    r = client(model).put("/documents/launch-plan", json={"title": "x"}, headers=as_user("bob"))
    assert r.status_code == status


@pytest.mark.parametrize("model", ["abac", "rebac", "hybrid"])
def test_carol_can_read_but_not_edit(client, model):
    c = client(model)
    assert c.get("/documents/launch-plan", headers=as_user("carol")).status_code == 200
    r = c.put("/documents/launch-plan", json={"title": "x"}, headers=as_user("carol"))
    assert r.status_code == 403


def test_list_is_filtered(client):
    r = client("rebac").get("/documents", headers=as_user("erin"))
    assert r.json()["documents"] == ["launch-plan", "brand-guide"]


def test_pep_fails_closed_when_pdp_is_down(client, monkeypatch):
    monkeypatch.setattr(api, "PDP_URL", "http://127.0.0.1:9")  # nothing listens here
    r = client("authzen").get("/documents/launch-plan", headers=as_user("alice"))
    assert r.status_code == 503


def test_authzen_evaluation_shape():
    c = TestClient(pdp.app)
    body = {"subject": {"type": "user", "id": "erin"}, "action": {"name": "can_edit"},
            "resource": {"type": "document", "id": "launch-plan"}}
    r = c.post("/access/v1/evaluation", json=body,
               headers={"Authorization": "Bearer demo-pep-key-not-secret"})
    assert r.status_code == 200          # a deny is still HTTP 200
    assert r.json() == {"decision": False}


def test_pdp_rejects_unknown_pep():
    r = TestClient(pdp.app).post("/access/v1/evaluation", json={})
    assert r.status_code == 401


@pytest.mark.parametrize("model", list(MODELS))
def test_unknown_action_is_denied(monkeypatch, model):
    monkeypatch.setattr(pdp, "PDP_MODEL", model)
    assert pdp.decide({"type": "user", "id": "dave"}, {"name": "can_share"},
                      {"type": "document", "id": "launch-plan"}) is False
