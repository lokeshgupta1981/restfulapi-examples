"""DEMO authorization server for learning only.

It has no login page and no consent screen. The demo user named in the
login_hint parameter is signed in automatically and approves every scope the
server is willing to grant. In production, use a real authorization server
such as Keycloak, Auth0, Okta or Microsoft Entra ID.

Run: uvicorn auth_server:app --port 8000
"""
import base64
import hashlib
import os
import re
import secrets
import time
import uuid
from urllib.parse import urlencode

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

ISSUER = os.environ.get("ISSUER", "http://127.0.0.1:8000")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001")
TOKEN_LIFETIME = 300

# Every scope the Bookstore API understands.
SCOPES = {"books:read", "orders:read", "orders:write", "orders:refund"}

# Demo users. A role describes the user, not the app.
USERS = {
    "asha": {"roles": ["customer"]},
    "ravi": {"roles": ["staff"]},
}
# Scopes a user may hand to an app. Only staff may refund orders.
SCOPES_FOR_ROLE = {
    "customer": {"books:read", "orders:read", "orders:write"},
    "staff": {"books:read", "orders:read", "orders:write", "orders:refund"},
}

# Registered clients and the scopes each one may ever receive.
# The secret is a fake demo value.
CLIENTS = {
    # Our own web shop (public client, PKCE, no secret).
    "bookshop-web": {"secret": None,
                     "scopes": {"books:read", "orders:read", "orders:write", "orders:refund"}},
    # A third-party reading tracker. It may only read.
    "reading-tracker": {"secret": "demo-secret-reading-tracker",
                        "scopes": {"books:read", "orders:read"}},
}
REDIRECT_URI = "http://127.0.0.1:8099/callback"

# RFC 6749, section 3.3: scope-token = 1*( %x21 / %x23-5B / %x5D-7E )
SCOPE_TOKEN = re.compile(r'^[\x21\x23-\x5B\x5D-\x7E]+$')

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KEY_ID = "demo-" + secrets.token_hex(4)
CODES = {}  # authorization code -> details, used once

app = FastAPI(title="Demo authorization server")


def parse_scope(raw):
    """Split a scope string. Returns None if a value breaks the RFC 6749 syntax."""
    values = raw.split(" ") if raw else []
    if any(not SCOPE_TOKEN.match(v) for v in values):
        return None
    return set(values)


def grant_scopes(requested, client_id, user):
    """The granted scope is what was asked for AND what the client AND the user may have."""
    user_may = set().union(*(SCOPES_FOR_ROLE[r] for r in USERS[user]["roles"]))
    return requested & CLIENTS[client_id]["scopes"] & user_may


def redirect_error(state, error, description):
    query = urlencode({"error": error, "error_description": description, "state": state})
    return RedirectResponse(f"{REDIRECT_URI}?{query}", status_code=302)


def oauth_error(error, description, status=400):
    return JSONResponse({"error": error, "error_description": description},
                        status_code=status, headers={"Cache-Control": "no-store"})


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    return {"issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
            "scopes_supported": sorted(SCOPES),
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"]}


@app.get("/.well-known/jwks.json")
def jwks():
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
    jwk.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})
    return {"keys": [jwk]}


@app.get("/authorize")
def authorize(response_type: str, client_id: str, redirect_uri: str, state: str,
              code_challenge: str, code_challenge_method: str,
              scope: str = "", login_hint: str = "asha"):
    if client_id not in CLIENTS or redirect_uri != REDIRECT_URI:
        return oauth_error("invalid_request", "Unknown client or redirect_uri")
    if response_type != "code" or code_challenge_method != "S256":
        return redirect_error(state, "invalid_request", "Use response_type=code and PKCE S256")

    requested = parse_scope(scope)
    if requested is None:
        return redirect_error(state, "invalid_scope", "Malformed scope value")
    if not requested:
        # RFC 6749 allows a default scope here; this server asks for an explicit one.
        return redirect_error(state, "invalid_scope", "The scope parameter is required")
    unknown = requested - SCOPES
    if unknown:
        return redirect_error(state, "invalid_scope", "Unknown scope: " + " ".join(sorted(unknown)))

    # DEMO: no login page and no consent screen. The user in login_hint approves.
    if login_hint not in USERS:
        return redirect_error(state, "access_denied", "Unknown demo user")
    granted = grant_scopes(requested, client_id, login_hint)
    if not granted:
        return redirect_error(state, "invalid_scope", "None of the requested scopes can be granted")

    code = secrets.token_urlsafe(24)
    CODES[code] = {"client_id": client_id, "user": login_hint, "scopes": granted,
                   "challenge": code_challenge, "expires": time.time() + 60}
    return RedirectResponse(f"{REDIRECT_URI}?{urlencode({'code': code, 'state': state})}",
                            status_code=302)


@app.post("/token")
def token(request: Request, grant_type: str = Form(...), code: str = Form(...),
          redirect_uri: str = Form(...), code_verifier: str = Form(...),
          client_id: str = Form(None), client_secret: str = Form(None)):
    # Confidential clients may authenticate with HTTP Basic.
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        client_id, _, client_secret = base64.b64decode(auth[6:]).decode().partition(":")
    client = CLIENTS.get(client_id)
    if client is None or (client["secret"] is not None and not (
            client_secret and secrets.compare_digest(client["secret"], client_secret))):
        return oauth_error("invalid_client", "Client authentication failed", 401)
    if grant_type != "authorization_code":
        return oauth_error("unsupported_grant_type", "Only authorization_code is supported")

    details = CODES.pop(code, None)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    if (details is None or details["client_id"] != client_id or redirect_uri != REDIRECT_URI
            or details["expires"] < time.time() or details["challenge"] != challenge):
        return oauth_error("invalid_grant", "Invalid, expired or used authorization code")

    now = int(time.time())
    scope = " ".join(sorted(details["scopes"]))
    claims = {"iss": ISSUER, "sub": details["user"], "aud": API_URL, "client_id": client_id,
              "scope": scope, "roles": USERS[details["user"]]["roles"],
              "iat": now, "exp": now + TOKEN_LIFETIME, "jti": str(uuid.uuid4())}
    access_token = jwt.encode(claims, PRIVATE_KEY, algorithm="RS256",
                              headers={"kid": KEY_ID, "typ": "at+jwt"})
    # This server always returns "scope". RFC 6749 requires it only when the
    # granted scope differs from the requested one.
    return JSONResponse({"access_token": access_token, "token_type": "Bearer",
                         "expires_in": TOKEN_LIFETIME, "scope": scope},
                        headers={"Cache-Control": "no-store"})
