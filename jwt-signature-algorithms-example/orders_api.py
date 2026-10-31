"""Demo Orders API that verifies JWT signatures before it trusts any claim.

The verifier never lets the token choose the algorithm. It looks up the key by the
token's "kid" header, and each key is bound to exactly one algorithm (RFC 8725, 3.1).
"""
import os

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ISSUER = os.environ.get("ISSUER_URL", "http://127.0.0.1:8000")
AUDIENCE = "orders-api"
HS256_SECRET = bytes.fromhex(os.environ["HS256_SECRET"])  # same secret as the issuer
HS256_KID = "hs-demo-1"

# Public keys come from the issuer's JWKS. PyJWKClient caches the key set for `lifespan`
# seconds. For an unknown kid it fetches the set again, but at most once per
# `cooldown_duration` seconds, so a flood of forged kids can't hammer the issuer.
jwks_client = jwt.PyJWKClient(ISSUER + "/.well-known/jwks.json", cache_keys=True,
                             lifespan=300, cooldown_duration=30)  # the PyJWT 2.15 defaults

app = FastAPI()


class InvalidToken(Exception):
    pass


@app.exception_handler(InvalidToken)
def invalid_token(request: Request, exc: InvalidToken):
    description = str(exc).replace('"', "'")  # keep the header's quoted-string valid
    return JSONResponse({"error": "invalid_token", "error_description": description}, status_code=401,
                        headers={"WWW-Authenticate": f'Bearer error="invalid_token", error_description="{description}"'})


def key_for(token):
    """Returns (key, alg) for the token's kid. The alg comes from our key table, not the token."""
    kid = jwt.get_unverified_header(token).get("kid")
    if kid == HS256_KID:
        return HS256_SECRET, "HS256"
    signing_key = jwks_client.get_signing_key(kid)  # raises PyJWKClientError for unknown kids
    return signing_key.key, signing_key.algorithm_name


def verify(request: Request) -> dict:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidToken("Bearer token missing")
    try:
        key, alg = key_for(token)
        return jwt.decode(token, key, algorithms=[alg], audience=AUDIENCE, issuer=ISSUER,
                          options={"require": ["exp", "iat", "sub"]})
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise InvalidToken(f"{type(exc).__name__}: {exc}")


@app.get("/orders")
def orders(request: Request):
    claims = verify(request)
    return {"customer": claims["sub"], "orders": [{"id": "ord_1001", "total": "49.90"}]}
