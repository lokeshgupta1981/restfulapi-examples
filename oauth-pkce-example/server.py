"""DEMO authorization server and Bookstore Orders API, for learning only.

It has no login page and signs in the demo user "asha" automatically. It keeps
codes and tokens in memory. In production, use a real authorization server
such as Keycloak, Auth0, Okta or Microsoft Entra ID.

PKCE_MODE=required (default): every authorization request needs an S256
                              code_challenge, and the token request must
                              present the matching code_verifier.
PKCE_MODE=optional          : PKCE is checked when the client sends a
                              code_challenge, like many OAuth 2.0 servers.
PKCE_MODE=off               : the server ignores PKCE completely, like an
                              old OAuth 2.0 server. Used to show the attack.

Run: uvicorn server:app --port 8000
"""
import base64
import hashlib
import os
import re
import secrets
import time
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse

PKCE_MODE = os.environ.get("PKCE_MODE", "required")
CODE_LIFETIME = 60  # seconds; codes are short-lived and used once

# One registered public client: the Bookstore mobile app. It has no secret.
CLIENTS = {
    "bookstore-app": {"redirect_uris": {"com.example.bookstore:/oauth/callback"}},
}
ORDERS = {"asha": [{"id": "ord-1001", "book": "REST in Practice", "total": 39.90},
                   {"id": "ord-1002", "book": "Designing Web APIs", "total": 44.50}]}
CODES = {}   # authorization code -> request details
TOKENS = {}  # access token -> user

VERIFIER_RE = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")    # RFC 7636, 4.1
CHALLENGE_RE = re.compile(r"^[A-Za-z0-9\-_]{43}$")         # S256 output

app = FastAPI(title="Demo authorization server + Bookstore API")


def s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def oauth_error(error, description, status=400):
    return JSONResponse({"error": error, "error_description": description},
                        status_code=status, headers={"Cache-Control": "no-store"})


@app.get("/.well-known/oauth-authorization-server")
def metadata(request: Request):
    base = str(request.base_url).rstrip("/")
    doc = {"issuer": base,
           "authorization_endpoint": base + "/authorize",
           "token_endpoint": base + "/token",
           "response_types_supported": ["code"],
           "grant_types_supported": ["authorization_code"],
           "token_endpoint_auth_methods_supported": ["none"]}
    if PKCE_MODE in ("required", "optional"):
        doc["code_challenge_methods_supported"] = ["S256"]
    return doc


@app.get("/authorize")
def authorize(response_type: str, client_id: str, redirect_uri: str,
              state: str = None, code_challenge: str = None,
              code_challenge_method: str = None):
    client = CLIENTS.get(client_id)
    # Never redirect to a URI we cannot trust: answer with an error page instead.
    if client is None or redirect_uri not in client["redirect_uris"]:
        return oauth_error("invalid_request", "unknown client or redirect_uri")

    def back(**params):
        if state is not None:
            params["state"] = state
        return RedirectResponse(redirect_uri + "?" + urlencode(params), status_code=302)

    if response_type != "code":
        return back(error="unsupported_response_type")

    if PKCE_MODE == "required" and not code_challenge:
        return back(error="invalid_request", error_description="code_challenge required")
    if PKCE_MODE in ("required", "optional") and code_challenge:
        if code_challenge_method != "S256":
            return back(error="invalid_request",
                        error_description="code_challenge_method must be S256")
        if not CHALLENGE_RE.match(code_challenge):
            return back(error="invalid_request", error_description="malformed code_challenge")
    if PKCE_MODE == "off":
        code_challenge = None  # ignore PKCE completely

    # A real server shows a login and consent page here. The demo user "asha"
    # is signed in automatically.
    code = secrets.token_urlsafe(32)
    CODES[code] = {"client_id": client_id, "redirect_uri": redirect_uri, "user": "asha",
                   "challenge": code_challenge, "expires": time.time() + CODE_LIFETIME}
    return back(code=code)


@app.post("/token")
def token(grant_type: str = Form(...), code: str = Form(...),
          redirect_uri: str = Form(...), client_id: str = Form(...),
          code_verifier: str = Form(None)):
    if grant_type != "authorization_code":
        return oauth_error("unsupported_grant_type", "only authorization_code")

    # A code is used once, even if this attempt fails.
    grant = CODES.pop(code, None)
    if grant is None or grant["expires"] < time.time():
        return oauth_error("invalid_grant", "unknown, used or expired code")
    if grant["client_id"] != client_id or grant["redirect_uri"] != redirect_uri:
        return oauth_error("invalid_grant", "client_id or redirect_uri mismatch")

    if PKCE_MODE in ("required", "optional"):
        if grant["challenge"] is None:
            # Downgrade protection (RFC 9700, 4.8.2): no challenge was sent,
            # so a verifier here means someone removed the challenge.
            if code_verifier is not None:
                return oauth_error("invalid_request", "code_verifier without code_challenge")
        else:
            if code_verifier is None:
                return oauth_error("invalid_grant", "code_verifier required")
            if not VERIFIER_RE.match(code_verifier):
                return oauth_error("invalid_grant", "malformed code_verifier")
            if not secrets.compare_digest(s256(code_verifier), grant["challenge"]):
                return oauth_error("invalid_grant", "code_verifier does not match code_challenge")

    access_token = secrets.token_urlsafe(32)
    TOKENS[access_token] = grant["user"]
    return JSONResponse({"access_token": access_token, "token_type": "Bearer",
                         "expires_in": 3600}, headers={"Cache-Control": "no-store"})


@app.get("/orders")
def orders(authorization: str = Header(None)):
    user = None
    if authorization and authorization.startswith("Bearer "):
        user = TOKENS.get(authorization[len("Bearer "):])
    if user is None:
        return JSONResponse({"error": "invalid_token"}, status_code=401,
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    return {"user": user, "orders": ORDERS[user]}
