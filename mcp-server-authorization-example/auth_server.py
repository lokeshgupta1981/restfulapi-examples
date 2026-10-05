"""Minimal OAuth 2.1 style authorization server for the demo.

It supports one flow: authorization code with PKCE (S256), a required
resource parameter (RFC 8707) and pre-registered public clients.
It signs JWT access tokens (RFC 9068 profile) with an RSA key that is
created at startup. Demo only: there is no login page, the user "asha"
is always signed in and always approves.
"""

import base64
import hashlib
import secrets
import time
import uuid
from urllib.parse import urlencode

import jwt
import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

ISSUER = "http://127.0.0.1:9420"
TOKEN_LIFETIME_SECONDS = 300
DEMO_USER = "asha"

# Pre-registered public clients (no client secret, PKCE is required).
CLIENTS = {
    "orders-desktop": {
        "redirect_uris": ["http://127.0.0.1:9499/callback"],
    },
}

# Resources (APIs and MCP servers) this server issues tokens for,
# with the scopes each one accepts.
RESOURCES = {
    "http://127.0.0.1:9410/mcp": ["orders:read", "orders:write"],
    "http://127.0.0.1:9430/reports": ["reports:read"],
}

SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KEY_ID = "demo-key-1"

# Authorization codes waiting to be exchanged (in memory, single use).
PENDING_CODES: dict[str, dict] = {}


def oauth_error(error: str, description: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": error, "error_description": description}, status_code=status)


async def metadata(request: Request) -> JSONResponse:
    """RFC 8414 authorization server metadata."""
    return JSONResponse(
        {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/jwks.json",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": sorted({s for scopes in RESOURCES.values() for s in scopes}),
            "authorization_response_iss_parameter_supported": True,
        }
    )


async def jwks(request: Request) -> JSONResponse:
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    public_jwk.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})
    return JSONResponse({"keys": [public_jwk]})


async def authorize(request: Request):
    params = request.query_params
    client_id = params.get("client_id")
    redirect_uri = params.get("redirect_uri")

    # Never redirect to an unknown URI: show the error to the user instead.
    client = CLIENTS.get(client_id)
    if client is None or redirect_uri not in client["redirect_uris"]:
        return oauth_error("invalid_request", "unknown client_id or redirect_uri")

    def fail(error: str, description: str) -> RedirectResponse:
        query = urlencode({"error": error, "error_description": description,
                           "state": params.get("state", ""), "iss": ISSUER})
        return RedirectResponse(f"{redirect_uri}?{query}", status_code=302)

    if params.get("response_type") != "code":
        return fail("unsupported_response_type", "only response_type=code is supported")
    if params.get("code_challenge_method") != "S256" or not params.get("code_challenge"):
        return fail("invalid_request", "PKCE with S256 is required")

    resource = params.get("resource")
    if resource not in RESOURCES:
        return fail("invalid_target", "resource parameter is missing or unknown")

    requested = params.get("scope", "").split()
    if not requested or any(s not in RESOURCES[resource] for s in requested):
        return fail("invalid_scope", f"allowed scopes for this resource: {' '.join(RESOURCES[resource])}")

    # A real server shows a login and consent page here. The demo user approves.
    code = secrets.token_urlsafe(24)
    PENDING_CODES[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": params["code_challenge"],
        "resource": resource,
        "scope": " ".join(requested),
        "user": DEMO_USER,
        "expires_at": time.time() + 60,
    }
    query = urlencode({"code": code, "state": params.get("state", ""), "iss": ISSUER})
    return RedirectResponse(f"{redirect_uri}?{query}", status_code=302)


def s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


async def token(request: Request) -> JSONResponse:
    form = await request.form()
    if form.get("grant_type") != "authorization_code":
        return oauth_error("unsupported_grant_type", "only authorization_code is supported")

    pending = PENDING_CODES.pop(form.get("code", ""), None)
    if pending is None or pending["expires_at"] < time.time():
        return oauth_error("invalid_grant", "unknown, used or expired code")
    if form.get("client_id") != pending["client_id"] or form.get("redirect_uri") != pending["redirect_uri"]:
        return oauth_error("invalid_grant", "client_id or redirect_uri does not match the authorization request")
    if s256(form.get("code_verifier", "")) != pending["code_challenge"]:
        return oauth_error("invalid_grant", "PKCE code_verifier does not match code_challenge")
    if form.get("resource") != pending["resource"]:
        return oauth_error("invalid_target", "resource must match the authorization request")

    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": pending["user"],
        "aud": pending["resource"],
        "client_id": pending["client_id"],
        "scope": pending["scope"],
        "iat": now,
        "exp": now + TOKEN_LIFETIME_SECONDS,
        "jti": str(uuid.uuid4()),
    }
    access_token = jwt.encode(claims, SIGNING_KEY, algorithm="RS256",
                              headers={"kid": KEY_ID, "typ": "at+jwt"})
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": TOKEN_LIFETIME_SECONDS,
            "scope": pending["scope"],
        },
        headers={"Cache-Control": "no-store"},
    )


app = Starlette(
    routes=[
        Route("/.well-known/oauth-authorization-server", metadata),
        Route("/jwks.json", jwks),
        Route("/authorize", authorize),
        Route("/token", token, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9420, log_level="warning")
