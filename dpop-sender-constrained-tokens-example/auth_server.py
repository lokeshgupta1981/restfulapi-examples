"""Demo authorization server: client credentials grant, DPoP-bound or plain bearer tokens.

For learning only. Use a real authorization server (Keycloak, Auth0, Okta, Entra ID, ...)
in production. The client secret below is a fake demo value.
"""
import base64
import os
import secrets
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse

import dpop

ISSUER = os.environ.get("ISSUER", "http://localhost:8000")
API_AUDIENCE = "orders-api"
CLIENTS = {"orders-app": "demo-secret-not-for-production"}     # fake demo secret
TOKEN_LIFETIME = 300

signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KID = "demo-key-1"
replay = dpop.ReplayCache()
app = FastAPI()


def oauth_error(status: int, error: str, description: str):
    return JSONResponse({"error": error, "error_description": description}, status_code=status)


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    return {"issuer": ISSUER, "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/jwks.json",
            "grant_types_supported": ["client_credentials"],
            "dpop_signing_alg_values_supported": dpop.ALGS}


@app.get("/jwks.json")
def jwks():
    nums = signing_key.public_key().public_numbers()
    def enc(i):
        return dpop.b64url(i.to_bytes((i.bit_length() + 7) // 8, "big"))
    return {"keys": [{"kty": "RSA", "kid": KID, "use": "sig", "alg": "RS256",
                      "n": enc(nums.n), "e": enc(nums.e)}]}


@app.post("/token")
async def token(request: Request, grant_type: str = Form(...), scope: str = Form("orders:read")):
    client_id, secret = basic_auth(request)
    if CLIENTS.get(client_id) != secret:
        return oauth_error(401, "invalid_client", "unknown client or wrong secret")
    if grant_type != "client_credentials":
        return oauth_error(400, "unsupported_grant_type", "only client_credentials")

    claims = {"iss": ISSUER, "sub": client_id, "aud": API_AUDIENCE, "scope": scope,
              "iat": int(time.time()), "exp": int(time.time()) + TOKEN_LIFETIME,
              "jti": secrets.token_urlsafe(8)}
    token_type = "Bearer"

    proofs = request.headers.getlist("dpop")
    if proofs:                                    # the client asked for a DPoP-bound token
        try:
            jkt = dpop.verify_proof(proofs, "POST", f"{ISSUER}/token", replay)
        except dpop.DPoPError as e:
            return oauth_error(400, e.error, e.description)
        claims["cnf"] = {"jkt": jkt}              # bind the token to the client's public key
        token_type = "DPoP"

    access_token = jwt.encode(claims, signing_key, algorithm="RS256",
                              headers={"kid": KID, "typ": "at+jwt"})
    return JSONResponse({"access_token": access_token, "token_type": token_type,
                         "expires_in": TOKEN_LIFETIME, "scope": scope},
                        headers={"Cache-Control": "no-store"})


def basic_auth(request: Request):
    value = request.headers.get("authorization", "")
    if not value.lower().startswith("basic "):
        return None, None
    user, _, pw = base64.b64decode(value[6:]).decode().partition(":")
    return user, pw
