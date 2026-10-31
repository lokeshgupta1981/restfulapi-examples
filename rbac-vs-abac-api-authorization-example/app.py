"""Docs API: the same endpoints, protected by RBAC, ABAC, ReBAC or an AuthZEN PDP.

AUTHZ_MODEL=rbac|abac|rebac  decide in process with policies.py
AUTHZ_MODEL=authzen          ask the PDP at PDP_URL (see pdp.py)

Run: AUTHZ_MODEL=abac uvicorn app:app --port 8000
"""

import copy
import os

import httpx2
from fastapi import Depends, FastAPI, Header, HTTPException

from data import DOCUMENTS, TOKENS, USERS
from policies import MODELS

AUTHZ_MODEL = os.environ.get("AUTHZ_MODEL", "rebac")
PDP_URL = os.environ.get("PDP_URL", "http://127.0.0.1:8001")
PDP_KEY = os.environ.get("PDP_KEY", "demo-pep-key-not-secret")

app = FastAPI(title=f"Docs API ({AUTHZ_MODEL})")
docs = copy.deepcopy(DOCUMENTS)


# ------------------------------------------------------------ authentication
def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token",
                            headers={"WWW-Authenticate": 'Bearer realm="docs-api"'})
    user_id = TOKENS.get(authorization.removeprefix("Bearer "))
    if user_id is None:
        raise HTTPException(401, "Unknown token",
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    return USERS[user_id]


# ------------------------------------------------------------ authorization
def ask_pdp(user, actions, doc):
    """One AuthZEN batch call: one decision per action, same order."""
    body = {
        "subject": {"type": "user", "id": user["id"]},
        "resource": {"type": "document", "id": doc["id"]},
        "evaluations": [{"action": {"name": f"can_{a}"}} for a in actions],
    }
    try:
        r = httpx2.post(f"{PDP_URL}/access/v1/evaluations", json=body, timeout=2.0,
                        headers={"Authorization": f"Bearer {PDP_KEY}"})
        r.raise_for_status()
        return [e["decision"] is True for e in r.json()["evaluations"]]
    except httpx2.HTTPError:
        # Fail closed: no answer from the PDP means no access.
        raise HTTPException(503, "Authorization service unavailable")


def allowed(user, action, doc):
    if AUTHZ_MODEL == "authzen":
        return ask_pdp(user, [action], doc)[0]
    return MODELS[AUTHZ_MODEL](user, action, doc)


def load_document(doc_id, user, action):
    """Load the document, then enforce. 404 hides documents the user may not read."""
    doc = docs.get(doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    if action == "read":
        if not allowed(user, "read", doc):
            raise HTTPException(404, "Document not found")
    else:
        if AUTHZ_MODEL == "authzen":
            can_read, can_act = ask_pdp(user, ["read", action], doc)
        else:
            can_read, can_act = allowed(user, "read", doc), allowed(user, action, doc)
        if not can_read:
            raise HTTPException(404, "Document not found")
        if not can_act:
            raise HTTPException(403, f"Not allowed to {action} this document")
    return doc


# ------------------------------------------------------------ endpoints
@app.get("/documents")
def list_documents(user=Depends(current_user)):
    visible = [d for d in docs.values() if allowed(user, "read", d)]
    return {"model": AUTHZ_MODEL, "documents": [d["id"] for d in visible]}


@app.get("/documents/{doc_id}")
def read_document(doc_id: str, user=Depends(current_user)):
    return load_document(doc_id, user, "read")


@app.put("/documents/{doc_id}")
def edit_document(doc_id: str, change: dict, user=Depends(current_user)):
    doc = load_document(doc_id, user, "edit")
    doc["title"] = change.get("title", doc["title"])
    return doc


@app.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, user=Depends(current_user)):
    load_document(doc_id, user, "delete")
    del docs[doc_id]
