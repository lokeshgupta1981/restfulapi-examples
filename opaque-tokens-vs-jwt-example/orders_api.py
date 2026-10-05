"""Demo Orders API (resource server) that validates access tokens three ways:

  /jwt/orders         local JWT check with the issuer's JWKS (RFC 9068)
  /introspect/orders  a call to the introspection endpoint on every request (RFC 7662)
  /cached/orders      introspection with a short in-memory cache
"""
import hashlib
import os
import time

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ISSUER = "http://127.0.0.1:9400"
API_AUDIENCE = "https://api.example.com/orders"
JWKS_URL = ISSUER + "/jwks"
INTROSPECTION_URL = ISSUER + "/introspect"
# Demo credentials of this API at the introspection endpoint.
API_CREDENTIALS = ("orders-api", "demo-introspect-secret-456")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "10"))  # seconds, our example value
REQUIRED_SCOPE = "orders:read"

jwks_client = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=300)
introspection_client = httpx.Client(auth=API_CREDENTIALS, timeout=2.0)
introspection_cache = {}  # sha256(token) -> (cached_until, claims)

ORDERS = [{"id": "ord_1001", "total": "49.90"}, {"id": "ord_1002", "total": "15.00"}]

app = FastAPI()


class TokenError(Exception):
    def __init__(self, status, error, description):
        self.status, self.error, self.description = status, error, description


@app.exception_handler(TokenError)
def token_error_handler(request: Request, exc: TokenError):
    challenge = f'Bearer error="{exc.error}", error_description="{exc.description}"'
    if exc.error == "insufficient_scope":
        challenge += f', scope="{REQUIRED_SCOPE}"'
    return JSONResponse(
        {"error": exc.error, "error_description": exc.description},
        status_code=exc.status,
        headers={"WWW-Authenticate": challenge},
    )


def bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise TokenError(401, "invalid_request", "Bearer token missing")
    return value.strip()


def validate_jwt(token_value: str) -> dict:
    try:
        header = jwt.get_unverified_header(token_value)
        if header.get("typ") not in ("at+jwt", "application/at+jwt"):
            raise TokenError(401, "invalid_token", "Not a JWT access token")
        signing_key = jwks_client.get_signing_key_from_jwt(token_value)
        return jwt.decode(
            token_value,
            signing_key.key,
            algorithms=["RS256"],
            audience=API_AUDIENCE,
            issuer=ISSUER,
            leeway=30,
            options={"require": ["iss", "sub", "aud", "exp", "iat", "jti", "client_id"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(401, "invalid_token", type(exc).__name__)


def introspect(token_value: str) -> dict:
    response = introspection_client.post(INTROSPECTION_URL, data={"token": token_value})
    response.raise_for_status()
    claims = response.json()
    if not claims.get("active"):
        raise TokenError(401, "invalid_token", "Token is not active")
    audiences = claims.get("aud")
    if not isinstance(audiences, list):
        audiences = [audiences]
    if API_AUDIENCE not in audiences:
        raise TokenError(401, "invalid_token", "Wrong audience")
    return claims


def introspect_cached(token_value: str) -> dict:
    key = hashlib.sha256(token_value.encode()).hexdigest()
    entry = introspection_cache.get(key)
    now = time.time()
    if entry and entry[0] > now:
        return entry[1]
    claims = introspect(token_value)
    # Never cache past the token's own exp (RFC 7662 section 4).
    introspection_cache[key] = (min(now + CACHE_TTL, claims["exp"]), claims)
    return claims


def require_scope(claims: dict, scope: str):
    if scope not in claims.get("scope", "").split():
        raise TokenError(403, "insufficient_scope", scope + " required")


def orders_response(claims: dict, validated_by: str, started: float):
    require_scope(claims, REQUIRED_SCOPE)
    auth_ms = (time.perf_counter() - started) * 1000
    return JSONResponse(
        {"validated_by": validated_by, "client_id": claims["client_id"], "orders": ORDERS},
        headers={"Server-Timing": f"auth;dur={auth_ms:.3f}"},
    )


@app.get("/jwt/orders")
def orders_jwt(request: Request):
    started = time.perf_counter()
    claims = validate_jwt(bearer_token(request))
    return orders_response(claims, "jwt-signature", started)


@app.get("/introspect/orders")
def orders_introspect(request: Request):
    started = time.perf_counter()
    claims = introspect(bearer_token(request))
    return orders_response(claims, "introspection", started)


@app.get("/cached/orders")
def orders_cached(request: Request):
    started = time.perf_counter()
    claims = introspect_cached(bearer_token(request))
    return orders_response(claims, "introspection-cached", started)
