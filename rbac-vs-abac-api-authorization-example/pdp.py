"""A small Policy Decision Point that speaks the OpenID AuthZEN Authorization API 1.0.

POST /access/v1/evaluation    one decision
POST /access/v1/evaluations   several decisions in one call
GET  /.well-known/authzen-configuration

PDP_MODEL=rbac|abac|rebac picks the policy (default rebac).
Run: PDP_MODEL=rebac uvicorn pdp:app --port 8001
"""

import os

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from data import DOCUMENTS, USERS
from policies import MODELS

PDP_MODEL = os.environ.get("PDP_MODEL", "rebac")
PDP_KEY = os.environ.get("PDP_KEY", "demo-pep-key-not-secret")

KNOWN_ACTIONS = {"can_read": "read", "can_edit": "edit", "can_delete": "delete"}

app = FastAPI(title=f"AuthZEN PDP ({PDP_MODEL})")


def authenticated_pep(authorization: str | None = Header(default=None)):
    # Only our own APIs (the PEPs) may ask for decisions.
    if authorization != f"Bearer {PDP_KEY}":
        raise HTTPException(401, "Unknown PEP", headers={"WWW-Authenticate": "Bearer"})


def decide(subject, action, resource):
    user = USERS.get(subject.get("id"))
    doc = DOCUMENTS.get(resource.get("id"))
    verb = KNOWN_ACTIONS.get(action.get("name"))
    if (user is None or doc is None or verb is None
            or subject.get("type") != "user" or resource.get("type") != "document"):
        return False  # anything we do not understand is a deny
    return MODELS[PDP_MODEL](user, verb, doc)


@app.get("/.well-known/authzen-configuration")
def metadata(request: Request):
    base = str(request.base_url).rstrip("/")
    return {
        "policy_decision_point": base,
        "access_evaluation_endpoint": f"{base}/access/v1/evaluation",
        "access_evaluations_endpoint": f"{base}/access/v1/evaluations",
    }


@app.post("/access/v1/evaluation", dependencies=[Depends(authenticated_pep)])
def evaluation(body: dict):
    return {"decision": decide(body.get("subject", {}), body.get("action", {}),
                               body.get("resource", {}))}


@app.post("/access/v1/evaluations", dependencies=[Depends(authenticated_pep)])
def evaluations(body: dict):
    results = []
    for item in body.get("evaluations", []):
        # Top-level subject, action and resource are defaults for each item.
        subject = item.get("subject", body.get("subject", {}))
        action = item.get("action", body.get("action", {}))
        resource = item.get("resource", body.get("resource", {}))
        results.append({"decision": decide(subject, action, resource)})
    return {"evaluations": results}
