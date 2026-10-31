"""Demo authorization server that signs JWT access tokens and publishes its JWKS.

Endpoints:
  GET  /.well-known/oauth-authorization-server   RFC 8414 metadata with jwks_uri
  GET  /.well-known/jwks.json                     the JWK Set (public keys only)
  POST /token                                     client credentials grant, returns a JWT
  POST /admin/keys                                demo only: create a key (next or active)
  POST /admin/keys/{kid}/activate                 demo only: sign new tokens with this key
  DELETE /admin/keys/{kid}                        demo only: remove a key from the JWKS

The /admin endpoints have no authentication. They exist only to drive the demo.
All keys are generated in memory at start-up and are demo keys.
"""
import base64
import os
import time
import uuid
from urllib.parse import parse_qs

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

ISSUER = os.environ.get("ISSUER", "http://127.0.0.1:8000")
AUDIENCE = "orders-api"
TOKEN_SECONDS = 600
# Demo client. Not a real secret.
CLIENTS = {"orders-app": "demo-secret-not-real"}

app = FastAPI()

# kid -> {"private": key, "alg": "RS256" | "ES256", "status": "active" | "next" | "retired"}
KEYS = {}


def new_key(kty: str):
    if kty == "EC":
        return ec.generate_private_key(ec.SECP256R1()), "ES256"
    return rsa.generate_private_key(public_exponent=65537, key_size=2048), "RS256"


def add_key(kid: str, kty: str, status: str):
    private, alg = new_key(kty)
    KEYS[kid] = {"private": private, "alg": alg, "status": status}
    if status == "active":
        for other_kid, other in KEYS.items():
            if other_kid != kid and other["status"] == "active":
                other["status"] = "retired"


def public_jwk(kid: str, entry: dict) -> dict:
    public = entry["private"].public_key()
    if entry["alg"] == "ES256":
        jwk_dict = ECAlgorithm.to_jwk(public, as_dict=True)
    else:
        jwk_dict = RSAAlgorithm.to_jwk(public, as_dict=True)
    jwk_dict.pop("key_ops", None)
    return {**jwk_dict, "kid": kid, "use": "sig", "alg": entry["alg"]}


add_key(os.environ.get("FIRST_KID", "2026-10-a"), "RSA", "active")


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    return {
        "issuer": ISSUER,
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic"],
    }


@app.get("/.well-known/jwks.json")
def jwks():
    keys = [public_jwk(kid, e) for kid, e in KEYS.items()]
    return JSONResponse({"keys": keys}, headers={"Cache-Control": "public, max-age=300"})


@app.post("/token")
async def token(request: Request):
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    auth = request.headers.get("authorization", "")
    try:
        client_id, secret = base64.b64decode(auth.removeprefix("Basic ")).decode().split(":", 1)
    except Exception:
        client_id, secret = "", ""
    if CLIENTS.get(client_id) != secret:
        return JSONResponse({"error": "invalid_client"}, status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="token"'})
    if form.get("grant_type") != "client_credentials":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    kid, entry = next((k, e) for k, e in KEYS.items() if e["status"] == "active")
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": client_id, "aud": AUDIENCE, "client_id": client_id,
              "scope": "orders:read", "iat": now, "exp": now + TOKEN_SECONDS,
              "jti": str(uuid.uuid4())}
    access_token = jwt.encode(claims, entry["private"], algorithm=entry["alg"],
                              headers={"kid": kid, "typ": "at+jwt"})
    return {"access_token": access_token, "token_type": "Bearer",
            "expires_in": TOKEN_SECONDS, "scope": "orders:read"}


@app.post("/admin/keys")
async def create_key(request: Request):
    body = await request.json()
    kid, kty, status = body["kid"], body.get("kty", "RSA"), body.get("status", "next")
    if kid in KEYS:
        raise HTTPException(409, "kid exists")
    add_key(kid, kty, status)
    return {k: e["status"] for k, e in KEYS.items()}


@app.post("/admin/keys/{kid}/activate")
def activate(kid: str):
    if kid not in KEYS:
        raise HTTPException(404, "unknown kid")
    for other in KEYS.values():
        if other["status"] == "active":
            other["status"] = "retired"
    KEYS[kid]["status"] = "active"
    return {k: e["status"] for k, e in KEYS.items()}


@app.delete("/admin/keys/{kid}")
def remove(kid: str):
    if KEYS.get(kid, {}).get("status") == "active":
        raise HTTPException(409, "cannot remove the active key")
    KEYS.pop(kid, None)
    return {k: e["status"] for k, e in KEYS.items()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("AUTH_PORT", "8000")),
                log_level="warning")
