"""An orders API that publishes OAuth 2.0 Protected Resource Metadata (RFC 9728).

Run with:  uvicorn resource_server:app --port 8000
Set PRM_FAKE_RESOURCE=1 to publish metadata for another resource, so the client
can show how it rejects a document that does not match.
"""
import json
import os
import urllib.parse
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

RESOURCE = "http://127.0.0.1:8000/orders"  # resource identifier, use https in production
METADATA_URL = "http://127.0.0.1:8000/.well-known/oauth-protected-resource/orders"
AUTH_SERVER = "http://127.0.0.1:9000"
ORDERS = [{"id": 101, "item": "Keyboard", "total": 49.0}, {"id": 102, "item": "Monitor", "total": 189.0}]

app = FastAPI()


@app.get("/.well-known/oauth-protected-resource/orders")
def protected_resource_metadata():
    resource = "https://orders.attacker.example/orders" if os.environ.get("PRM_FAKE_RESOURCE") else RESOURCE
    return {
        "resource": resource,
        "authorization_servers": [AUTH_SERVER],
        "scopes_supported": ["orders:read", "orders:write"],
        "bearer_methods_supported": ["header"],
        "resource_name": "Orders API",
        "resource_documentation": "http://127.0.0.1:8000/docs",
    }


def challenge(status, error=None, scope="orders:read"):
    params = [f'resource_metadata="{METADATA_URL}"', f'scope="{scope}"']
    if error:
        params.insert(0, f'error="{error}"')
    return JSONResponse({"error": error or "unauthorized"}, status_code=status,
                        headers={"WWW-Authenticate": "Bearer " + ", ".join(params)})


def introspect(token):
    body = urllib.parse.urlencode({"token": token}).encode()
    with urllib.request.urlopen(f"{AUTH_SERVER}/introspect", data=body, timeout=5) as resp:
        return json.load(resp)


@app.get("/orders")
def list_orders(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return challenge(401)
    info = introspect(auth.removeprefix("Bearer "))
    if not info["active"] or info["aud"] != RESOURCE:  # reject tokens issued for another resource
        return challenge(401, "invalid_token")
    if "orders:read" not in info["scope"].split():
        return challenge(403, "insufficient_scope")
    return ORDERS
