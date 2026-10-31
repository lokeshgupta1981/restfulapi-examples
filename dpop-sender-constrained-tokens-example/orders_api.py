"""Orders API (resource server) that accepts DPoP-bound access tokens.

Plain bearer tokens without a cnf claim are still accepted, so the demo can compare both.
Set REQUIRE_NONCE=1 to make the API demand a server nonce in every proof.
"""
import os
import secrets
import time

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import dpop

ISSUER = os.environ.get("ISSUER", "http://localhost:8000")
REQUIRE_NONCE = os.environ.get("REQUIRE_NONCE") == "1"
NONCE_LIFETIME = 300

replay = dpop.ReplayCache()
app = FastAPI()
ORDERS = [{"id": 1001, "item": "REST API Design book", "total": 39.0},
          {"id": 1002, "item": "HTTP pocket guide", "total": 12.5}]
_jwks = None
_nonce = {"value": secrets.token_urlsafe(16), "until": time.time() + NONCE_LIFETIME}


def current_nonce() -> str:
    if time.time() > _nonce["until"]:
        _nonce.update(value=secrets.token_urlsafe(16), until=time.time() + NONCE_LIFETIME)
    return _nonce["value"]


def issuer_key(kid: str):
    global _jwks
    if _jwks is None:
        _jwks = httpx.get(f"{ISSUER}/jwks.json").json()
    for k in _jwks["keys"]:
        if k["kid"] == kid:
            return jwt.PyJWK(k).key
    raise jwt.InvalidTokenError("unknown kid")


def challenge(error: str | None = None, description: str | None = None, nonce: bool = False):
    params = f'algs="{" ".join(dpop.ALGS)}"'
    if error:
        params = f'error="{error}", error_description="{description}", ' + params
    headers = {"WWW-Authenticate": f"DPoP {params}"}
    if nonce:
        headers["DPoP-Nonce"] = current_nonce()
    body = {"error": error or "unauthorized", "error_description": description or "token required"}
    return JSONResponse(body, status_code=401, headers=headers)


def authenticate(request: Request):
    """Returns the token claims, or a 401 response."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() not in ("bearer", "dpop") or not token:
        return challenge()
    try:
        claims = jwt.decode(token, issuer_key(jwt.get_unverified_header(token)["kid"]),
                            algorithms=["RS256"], audience="orders-api", issuer=ISSUER)
    except jwt.PyJWTError as e:
        return challenge("invalid_token", str(e))

    bound_jkt = claims.get("cnf", {}).get("jkt")
    if scheme.lower() == "bearer":
        if bound_jkt:      # RFC 9449, section 7.2: a DPoP-bound token must not work as Bearer
            return challenge("invalid_token", "DPoP-bound token sent with the Bearer scheme")
        return claims      # unbound bearer token: whoever holds it gets in
    if not bound_jkt:
        return challenge("invalid_token", "token is not DPoP-bound")

    try:
        jkt = dpop.verify_proof(request.headers.getlist("dpop"), request.method, str(request.url),
                                replay, access_token=token,
                                expected_nonce=current_nonce() if REQUIRE_NONCE else None)
    except dpop.DPoPError as e:
        return challenge(e.error, e.description, nonce=REQUIRE_NONCE)
    if jkt != bound_jkt:
        return challenge("invalid_dpop_proof", "proof key does not match the token's cnf.jkt")
    return claims


@app.get("/orders")
def list_orders(request: Request):
    auth = authenticate(request)
    if isinstance(auth, JSONResponse):
        return auth
    return {"client": auth["sub"], "orders": ORDERS}


@app.post("/orders")
async def create_order(request: Request):
    auth = authenticate(request)
    if isinstance(auth, JSONResponse):
        return auth
    order = {"id": 1000 + len(ORDERS) + 1, **(await request.json())}
    ORDERS.append(order)
    return JSONResponse(order, status_code=201)
