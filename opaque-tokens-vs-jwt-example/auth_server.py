"""Demo authorization server for the opaque token vs JWT example.

It issues opaque and JWT access tokens (client credentials grant),
publishes its public key as a JWKS, and offers token introspection
(RFC 7662) and token revocation (RFC 7009).

All keys and secrets here are demo values. Never use them in production.
"""
import base64
import json
import secrets
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import JSONResponse
from jwt.algorithms import RSAAlgorithm

ISSUER = "http://127.0.0.1:9400"
API_AUDIENCE = "https://api.example.com/orders"
KEY_ID = "demo-key-1"
TOKEN_LIFETIME = 300  # seconds

# Demo credentials only.
CLIENTS = {"orders-app": "demo-secret-key-123"}
RESOURCE_SERVERS = {"orders-api": "demo-introspect-secret-456"}

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
public_jwk.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})

opaque_tokens = {}  # opaque token -> claims
revoked_jtis = set()
stats = {"introspect": 0}

app = FastAPI()


def basic_auth(request: Request, registry: dict):
    """Returns the authenticated name from a Basic Authorization header, or None."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        return None
    try:
        name, secret = base64.b64decode(header[6:]).decode().split(":", 1)
    except Exception:
        return None
    if registry.get(name) == secret:
        return name
    return None


def unauthorized_client():
    return JSONResponse(
        {"error": "invalid_client"},
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="token-service"'},
    )


def sign_access_token(claims: dict) -> str:
    return jwt.encode(
        claims, private_key, algorithm="RS256",
        headers={"typ": "at+jwt", "kid": KEY_ID},
    )


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    return {
        "issuer": ISSUER,
        "token_endpoint": ISSUER + "/token",
        "jwks_uri": ISSUER + "/jwks",
        "introspection_endpoint": ISSUER + "/introspect",
        "revocation_endpoint": ISSUER + "/revoke",
    }


@app.get("/jwks")
def jwks():
    return {"keys": [public_jwk]}


@app.post("/token")
def token(
    request: Request,
    grant_type: str = Form(...),
    scope: str = Form("orders:read"),
    token_format: str = Form("jwt"),  # demo parameter: "jwt" or "opaque"
):
    client_id = basic_auth(request, CLIENTS)
    if client_id is None:
        return unauthorized_client()
    if grant_type != "client_credentials":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": client_id,
        "aud": API_AUDIENCE,
        "client_id": client_id,
        "scope": scope,
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
        "jti": str(uuid.uuid4()),
        # Extra claims that show what a JWT reveals to anyone holding it.
        "tenant": "acme-retail",
        "plan": "enterprise",
    }
    if token_format == "opaque":
        access_token = secrets.token_urlsafe(32)
        opaque_tokens[access_token] = claims
    else:
        access_token = sign_access_token(claims)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_LIFETIME,
        "scope": scope,
    }


def lookup(token_value: str):
    """Returns the claims of an active token, or None."""
    claims = opaque_tokens.get(token_value)
    if claims is None:
        try:
            claims = jwt.decode(
                token_value, private_key.public_key(), algorithms=["RS256"],
                audience=API_AUDIENCE, issuer=ISSUER,
            )
        except jwt.PyJWTError:
            return None
    if claims["exp"] <= time.time() or claims["jti"] in revoked_jtis:
        return None
    return claims


@app.post("/introspect")
def introspect(request: Request, token: str = Form(...)):
    if basic_auth(request, RESOURCE_SERVERS) is None:
        return unauthorized_client()
    stats["introspect"] += 1
    claims = lookup(token)
    if claims is None:
        return {"active": False}
    # Phantom token support: a gateway asks for the JWT form of an opaque token.
    if "application/jwt" in request.headers.get("accept", ""):
        return Response(sign_access_token(claims), media_type="application/jwt")
    return {"active": True, "token_type": "Bearer", **claims}


@app.post("/revoke")
def revoke(request: Request, token: str = Form(...)):
    if basic_auth(request, CLIENTS) is None:
        return unauthorized_client()
    claims = opaque_tokens.get(token)
    if claims is None:
        try:
            claims = jwt.decode(
                token, private_key.public_key(), algorithms=["RS256"],
                audience=API_AUDIENCE, options={"verify_exp": False},
            )
        except jwt.PyJWTError:
            claims = None
    if claims is not None:
        revoked_jtis.add(claims["jti"])
    # RFC 7009 section 2.2: HTTP 200 even for unknown tokens.
    return Response(status_code=200)


@app.get("/stats")
def get_stats():
    return stats


@app.post("/stats/reset")
def reset_stats():
    stats["introspect"] = 0
    return stats
