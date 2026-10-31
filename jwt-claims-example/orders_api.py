"""Orders API that validates the claims of a JWT access token.

Run: uvicorn orders_api:app --port 8000
"""
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tokens import AUDIENCE, ISSUER, PUBLIC_KEY

app = FastAPI()

TENANT_CLAIM = "https://bookstore.example/claims/tenant"
LEEWAY_SECONDS = 30

ORDERS = [
    {"id": "ord-1001", "tenant": "acme-books", "customer": "user-4711", "total": 42.50},
    {"id": "ord-1002", "tenant": "acme-books", "customer": "user-0815", "total": 18.00},
    {"id": "ord-2001", "tenant": "other-shop", "customer": "user-4711", "total": 99.90},
]


class AuthError(Exception):
    def __init__(self, status, error, description):
        self.status, self.error, self.description = status, error, description


@app.exception_handler(AuthError)
async def auth_error_handler(request, exc):
    description = exc.description.replace('"', "'")  # keep the header value well-formed
    challenge = f'Bearer error="{exc.error}", error_description="{description}"'
    return JSONResponse(status_code=exc.status,
                        content={"error": exc.error, "error_description": exc.description},
                        headers={"WWW-Authenticate": challenge})


def validate_access_token(token: str) -> dict:
    # 1. Explicit type: only accept JWT access tokens (RFC 9068), not ID tokens
    if jwt.get_unverified_header(token).get("typ") != "at+jwt":
        raise jwt.InvalidTokenError("typ is not at+jwt")
    # 2-5. Signature with a fixed algorithm, then iss, aud, exp, nbf, iat
    return jwt.decode(
        token,
        PUBLIC_KEY,
        algorithms=["RS256"],
        issuer=ISSUER,
        audience=AUDIENCE,
        leeway=LEEWAY_SECONDS,
        options={"require": ["iss", "sub", "aud", "exp", "iat", "jti"]},
    )


def authenticate(request: Request, needed_scope: str) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthError(401, "invalid_request", "Bearer token missing")
    try:
        claims = validate_access_token(auth.removeprefix("Bearer "))
    except jwt.InvalidTokenError as e:
        raise AuthError(401, "invalid_token", str(e))
    # Authorization: the scope claim lists what the token may do
    if needed_scope not in claims.get("scope", "").split():
        raise AuthError(403, "insufficient_scope", f"needs {needed_scope}")
    return claims


@app.get("/orders")
def list_orders(request: Request):
    claims = authenticate(request, "orders:read")
    tenant = claims.get(TENANT_CLAIM)
    mine = [o for o in ORDERS if o["tenant"] == tenant and o["customer"] == claims["sub"]]
    return {"tenant": tenant, "customer": claims["sub"], "orders": mine}


@app.post("/orders/{order_id}/refund")
def refund(order_id: str, request: Request):
    claims = authenticate(request, "orders:refund")
    return {"order": order_id, "refunded_by": claims["sub"]}
