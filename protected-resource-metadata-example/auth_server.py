"""A small authorization server for local testing. Do not deploy.

It publishes RFC 8414 authorization server metadata, issues access tokens with the
client credentials grant, and answers token introspection requests (RFC 7662).
"""
import secrets
import time

from fastapi import FastAPI, Form, HTTPException

ISSUER = "http://127.0.0.1:9000"
CLIENTS = {"orders-cli": "orders-cli-secret"}  # demo client, never hard-code real secrets
tokens = {}  # access token -> {"aud": ..., "scope": ..., "exp": ...}

app = FastAPI()


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    return {
        "issuer": ISSUER,
        "token_endpoint": f"{ISSUER}/token",
        "introspection_endpoint": f"{ISSUER}/introspect",
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["orders:read", "orders:write"],
        "protected_resources": ["http://127.0.0.1:8000/orders"],
    }


@app.post("/token")
def token(grant_type: str = Form(), client_id: str = Form(), client_secret: str = Form(),
          scope: str = Form(""), resource: str = Form("")):
    if grant_type != "client_credentials":
        raise HTTPException(400, detail={"error": "unsupported_grant_type"})
    if CLIENTS.get(client_id) != client_secret:
        raise HTTPException(401, detail={"error": "invalid_client"})
    value = secrets.token_urlsafe(24)
    # RFC 8707: the token is valid only for the resource the client asked for
    tokens[value] = {"aud": resource, "scope": scope, "exp": int(time.time()) + 600}
    return {"access_token": value, "token_type": "Bearer", "expires_in": 600, "scope": scope}


@app.post("/introspect")
def introspect(token: str = Form()):
    data = tokens.get(token)
    if not data or data["exp"] < time.time():
        return {"active": False}
    return {"active": True, **data}
