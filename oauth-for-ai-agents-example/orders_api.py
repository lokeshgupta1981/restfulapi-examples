"""Orders REST API (the resource server). It accepts only JWT access tokens
that the authorization server issued for this API.

Run: uvicorn orders_api:app --port 9201
"""
import logging

import httpx
import jwt
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

RESOURCE = "http://127.0.0.1:9201"   # this API's resource identifier
ISSUER = "http://127.0.0.1:9200"     # the only authorization server we trust
METADATA_URL = RESOURCE + "/.well-known/oauth-protected-resource"
_jwks = None


def jwks_client() -> jwt.PyJWKClient:
    """Read jwks_uri from the issuer's metadata (RFC 8414) on first use.
    PyJWKClient caches the key set for 5 minutes and fetches it again when it
    sees an unknown "kid" (at most once every 30 seconds)."""
    global _jwks
    if _jwks is None:
        meta = httpx.get(ISSUER + "/.well-known/oauth-authorization-server", timeout=5).json()
        if meta["issuer"] != ISSUER:
            raise RuntimeError("issuer metadata does not match")
        _jwks = jwt.PyJWKClient(meta["jwks_uri"])
    return _jwks


ORDERS = {
    "ord_1001": {"id": "ord_1001", "customer": "asha", "status": "shipped", "total": 59.90},
    "ord_1002": {"id": "ord_1002", "customer": "ben", "status": "pending", "total": 120.00},
    "ord_1003": {"id": "ord_1003", "customer": "asha", "status": "pending", "total": 18.50},
}

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="Orders API")


class KeysUnavailable(Exception):
    pass


class AuthError(Exception):
    def __init__(self, status, error=None, description=None, scope=None):
        self.status, self.error, self.description, self.scope = status, error, description, scope


@app.exception_handler(KeysUnavailable)
def keys_unavailable(request: Request, exc: KeysUnavailable):
    # Our problem, not the client's token: 503, so the client may retry later.
    return JSONResponse({"detail": "cannot check tokens right now"}, status_code=503,
                        headers={"Retry-After": "30"})


@app.exception_handler(AuthError)
def auth_error(request: Request, exc: AuthError):
    log.info("AUDIT-DENY %s %s status=%s error=%s", request.method, request.url.path,
             exc.status, exc.error or "no_token")
    # RFC 6750 section 3 challenge, plus resource_metadata from RFC 9728.
    parts = [f'resource_metadata="{METADATA_URL}"']
    if exc.error:
        parts.append(f'error="{exc.error}"')
        parts.append(f'error_description="{exc.description}"')
    if exc.scope:
        parts.append(f'scope="{exc.scope}"')
    if exc.error:
        body = {"error": exc.error, "error_description": exc.description}
    else:
        body = {"detail": "Bearer token required"}
    return JSONResponse(body, status_code=exc.status,
                        headers={"WWW-Authenticate": "Bearer " + ", ".join(parts)})


def require(scope: str):
    """Dependency: validate the bearer token and check one scope."""
    def check(request: Request) -> dict:
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            # No token: no error code (RFC 6750 section 3.1), but a scope hint.
            raise AuthError(401, scope=scope)
        token = token.strip()
        try:
            typ = str(jwt.get_unverified_header(token).get("typ", "")).lower()
            if typ not in ("at+jwt", "application/at+jwt"):  # RFC 9068 section 4
                raise jwt.InvalidTokenError("not a JWT access token (typ)")
            try:
                key = jwks_client().get_signing_key_from_jwt(token).key
            except (jwt.PyJWKClientConnectionError, httpx.HTTPError) as exc:
                raise KeysUnavailable() from exc
            claims = jwt.decode(token, key, algorithms=["RS256"], audience=RESOURCE,
                                issuer=ISSUER, leeway=30, options={"require": [
                                    "iss", "sub", "aud", "exp", "iat", "jti", "client_id"]})
        except jwt.PyJWTError as exc:
            # No double quotes inside the header value.
            raise AuthError(401, "invalid_token", str(exc).replace('"', "'"))
        if scope not in claims.get("scope", "").split():
            raise AuthError(403, "insufficient_scope", f"requires {scope}", scope)
        actor = claims.get("act", {}).get("sub", "-")
        log.info("AUDIT %s %s sub=%s actor=%s scope=%s", request.method,
                 request.url.path, claims["sub"], actor, claims["scope"])
        return claims
    return check


def visible_orders(claims: dict) -> list[dict]:
    # Only the scope orders:read:all shows every customer's orders. Every other
    # token, with or without an agent, sees only the orders of its subject.
    if "orders:read:all" in claims["scope"].split():
        return list(ORDERS.values())
    return [o for o in ORDERS.values() if o["customer"] == claims["sub"]]


@app.get("/.well-known/oauth-protected-resource")
def resource_metadata():
    return {"resource": RESOURCE, "authorization_servers": [ISSUER],
            "scopes_supported": ["orders:read", "orders:read:all", "orders:write"],
            "bearer_methods_supported": ["header"]}


@app.get("/orders")
def list_orders(claims: dict = Depends(require("orders:read"))):
    return visible_orders(claims)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, claims: dict = Depends(require("orders:write"))):
    order = next((o for o in visible_orders(claims) if o["id"] == order_id), None)
    if order is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    if order["status"] != "pending":
        return JSONResponse({"error": "conflict", "detail": "order is not pending"},
                            status_code=409)
    order["status"] = "cancelled"
    return order
