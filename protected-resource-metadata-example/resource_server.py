"""An orders API that publishes OAuth 2.0 Protected Resource Metadata (RFC 9728).

Run with:  uvicorn resource_server:app --port 8000
Set PRM_FAKE_RESOURCE=1 to publish metadata for another resource, so the client
can show how it rejects a document that does not match.
Set PRM_NO_HEADER=1 to leave resource_metadata out of the 401 challenge, so the
client has to build the well-known URL itself.
"""
import json
import os
import urllib.parse
import urllib.request

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

RESOURCE = "http://127.0.0.1:8000/orders"  # resource identifier, use https in production
METADATA_URL = "http://127.0.0.1:8000/.well-known/oauth-protected-resource/orders"
AUTH_SERVER = "http://127.0.0.1:9000"
ORDERS = [{"id": 101, "item": "Keyboard", "total": 49.0}, {"id": 102, "item": "Monitor", "total": 189.0}]

app = FastAPI()


@app.get("/.well-known/oauth-protected-resource/orders")
def protected_resource_metadata(response: Response):
    response.headers["Cache-Control"] = "max-age=3600"  # clients may reuse the document for an hour
    resource, auth_server = RESOURCE, AUTH_SERVER
    if os.environ.get("PRM_FAKE_RESOURCE"):  # a document copied from another site, with its own login server
        resource, auth_server = "https://orders.attacker.example/orders", "https://login.attacker.example"
    return {
        "resource": resource,
        "authorization_servers": [auth_server],
        "scopes_supported": ["orders:read", "orders:write"],
        "bearer_methods_supported": ["header"],
        "resource_name": "Orders API",
        "resource_documentation": "http://127.0.0.1:8000/docs",
    }


def challenge(status, error=None, scope="orders:read"):
    params = [f'scope="{scope}"']
    if not os.environ.get("PRM_NO_HEADER"):
        params.insert(0, f'resource_metadata="{METADATA_URL}"')
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
