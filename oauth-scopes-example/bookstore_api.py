"""Bookstore API: a resource server that checks OAuth scopes.

Run: uvicorn bookstore_api:app --port 8001
"""
import itertools
import os

import jwt
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

ISSUER = os.environ.get("ISSUER", "http://127.0.0.1:8000")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001")
METADATA_URL = f"{API_URL}/.well-known/oauth-protected-resource"

jwks_client = jwt.PyJWKClient(f"{ISSUER}/.well-known/jwks.json")

BOOKS = [{"id": "b-1", "title": "RESTful Web APIs"}, {"id": "b-2", "title": "OAuth 2 in Action"}]
ORDERS = {
    "o-1001": {"id": "o-1001", "customer": "asha", "book": "b-1", "status": "paid"},
    "o-1002": {"id": "o-1002", "customer": "asha", "book": "b-2", "status": "paid"},
    "o-2001": {"id": "o-2001", "customer": "meera", "book": "b-1", "status": "paid"},
}
next_id = itertools.count(1003)

app = FastAPI(title="Bookstore API")


class ApiError(Exception):
    def __init__(self, status, detail, challenge=None):
        self.status, self.detail, self.challenge = status, detail, challenge


@app.exception_handler(ApiError)
def api_error(request, exc):
    headers = {"WWW-Authenticate": exc.challenge} if exc.challenge else {}
    titles = {401: "Unauthorized", 403: "Forbidden", 404: "Not Found"}
    return JSONResponse({"type": "about:blank", "title": titles[exc.status],
                         "status": exc.status, "detail": exc.detail},
                        status_code=exc.status, headers=headers,
                        media_type="application/problem+json")


def authenticate(request: Request) -> dict:
    """Return the token's claims, or raise 401."""
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        # No credentials: RFC 6750 says no error code here.
        raise ApiError(401, "No access token",
                       f'Bearer resource_metadata="{METADATA_URL}"')
    try:
        key = jwks_client.get_signing_key_from_jwt(token).key
        if jwt.get_unverified_header(token).get("typ") != "at+jwt":
            raise jwt.InvalidTokenError("not an access token")
        return jwt.decode(token, key, algorithms=["RS256"], audience=API_URL, issuer=ISSUER)
    except jwt.PyJWTError:
        raise ApiError(401, "The access token is invalid or expired",
                       'Bearer error="invalid_token", '
                       'error_description="The access token is invalid or expired"')


def require_scope(scope: str):
    """A FastAPI dependency: the token must be valid AND carry this scope."""
    def check(claims: dict = Depends(authenticate)) -> dict:
        granted = claims.get("scope", "").split()
        if scope not in granted:
            raise ApiError(403, f"This request needs the scope {scope}",
                           f'Bearer error="insufficient_scope", scope="{scope}", '
                           f'resource_metadata="{METADATA_URL}", '
                           f'error_description="This request needs the scope {scope}"')
        return claims
    return check


@app.get("/.well-known/oauth-protected-resource")
def protected_resource_metadata():
    # RFC 9728: tells clients which authorization server and scopes to use.
    return {"resource": API_URL, "authorization_servers": [ISSUER],
            "scopes_supported": ["books:read", "orders:read", "orders:write", "orders:refund"],
            "bearer_methods_supported": ["header"]}


@app.get("/books")
def list_books(claims: dict = Depends(require_scope("books:read"))):
    return BOOKS


@app.get("/orders")
def list_orders(claims: dict = Depends(require_scope("orders:read"))):
    # The scope says the app may read orders. Whose orders comes from "sub".
    return [o for o in ORDERS.values() if o["customer"] == claims["sub"]]


@app.get("/orders/{order_id}")
def get_order(order_id: str, claims: dict = Depends(require_scope("orders:read"))):
    order = ORDERS.get(order_id)
    is_staff = "staff" in claims.get("roles", [])
    if order is None or (order["customer"] != claims["sub"] and not is_staff):
        raise ApiError(404, f"Order {order_id} not found")
    return order


@app.post("/orders", status_code=201)
async def place_order(request: Request, claims: dict = Depends(require_scope("orders:write"))):
    body = await request.json()
    order = {"id": f"o-{next(next_id)}", "customer": claims["sub"],
             "book": body["book"], "status": "paid"}
    ORDERS[order["id"]] = order
    return order


@app.post("/orders/{order_id}/refund")
def refund_order(order_id: str, claims: dict = Depends(require_scope("orders:refund"))):
    order = ORDERS.get(order_id)
    if order is None:
        raise ApiError(404, f"Order {order_id} not found")
    order["status"] = "refunded"
    return order
