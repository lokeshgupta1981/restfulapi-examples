"""DEMO authorization server and Bookstore API for learning only.

One file, two rule sets. OAUTH_PROFILE=2.0 follows the original OAuth 2.0
rules (RFC 6749 and RFC 6750) the way many servers implemented them.
OAUTH_PROFILE=2.1 follows the OAuth 2.1 draft (draft-ietf-oauth-v2-1-16).

There is no login page: the demo user "asha" is signed in automatically.
Everything is kept in memory. In production, use a real authorization server
such as Keycloak, Auth0, Okta or Microsoft Entra ID.

Run:  OAUTH_PROFILE=2.0 uvicorn server:app --port 8000
      OAUTH_PROFILE=2.1 uvicorn server:app --port 8001
"""
import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

PROFILE = os.environ.get("OAUTH_PROFILE", "2.1")
ISSUER = os.environ.get("ISSUER", "http://127.0.0.1:8000")
if PROFILE not in ("2.0", "2.1"):
    raise SystemExit("OAUTH_PROFILE must be 2.0 or 2.1")

# The Bookstore single-page app: a public client (no secret).
# Under 2.0 it registered only the start of its redirect URI, which RFC 6749
# allows as a fallback. Under 2.1 the complete URI must be registered.
CLIENTS = {
    "bookstore-spa": {
        "redirect_uri": "https://bookstore.example" if PROFILE == "2.0"
        else "https://bookstore.example/callback",
    }
}
USERS = {"asha": "demo-password-asha"}     # fake demo password

CODES = {}           # authorization code -> details (used once)
ACCESS_TOKENS = {}   # access token -> user
REFRESH_TOKENS = {}  # refresh token -> {"user", "family", "active"}
REVOKED_FAMILIES = set()

app = FastAPI(title=f"Demo OAuth {PROFILE} server")


def error(code, description, status=400):
    return JSONResponse({"error": code, "error_description": description}, status_code=status)


def redirect_ok(client, redirect_uri):
    registered = client["redirect_uri"]
    if PROFILE == "2.0":
        return redirect_uri.startswith(registered)   # lenient prefix match
    return redirect_uri == registered                 # exact string match


def issue_tokens(user, family=None):
    access = secrets.token_urlsafe(16)
    ACCESS_TOKENS[access] = user
    refresh = secrets.token_urlsafe(16)
    REFRESH_TOKENS[refresh] = {"user": user, "family": family or secrets.token_hex(4),
                               "active": True}
    return {"access_token": access, "token_type": "Bearer", "expires_in": 600,
            "refresh_token": refresh, "scope": "books:read"}


@app.get("/authorize")
def authorize(client_id: str, response_type: str, redirect_uri: str | None = None,
              state: str | None = None, code_challenge: str | None = None,
              code_challenge_method: str | None = None):
    client = CLIENTS.get(client_id)
    if client is None:
        return error("invalid_request", "unknown client_id")
    sent_redirect_uri = redirect_uri
    redirect_uri = redirect_uri or client["redirect_uri"]
    if not redirect_ok(client, redirect_uri):
        # Never redirect to an unverified URI: show the error to the user instead.
        return error("invalid_request", "redirect_uri does not match the registered value")

    def back(params, fragment=False):
        if state:
            params["state"] = state
        sep = "#" if fragment else ("&" if "?" in redirect_uri else "?")
        return RedirectResponse(redirect_uri + sep + urlencode(params), status_code=302)

    iss = {"iss": ISSUER} if PROFILE == "2.1" else {}

    if response_type == "token":
        if PROFILE == "2.1":
            return back({"error": "unsupported_response_type",
                         "error_description": "the implicit grant is not part of OAuth 2.1", **iss})
        tokens = issue_tokens("asha")
        tokens.pop("refresh_token")       # the implicit grant never returned refresh tokens
        return back({k: str(v) for k, v in tokens.items()}, fragment=True)

    if response_type != "code":
        return back({"error": "unsupported_response_type", **iss})

    if PROFILE == "2.1":
        if not code_challenge:
            return back({"error": "invalid_request",
                         "error_description": "code_challenge is required", **iss})
        if code_challenge_method != "S256":
            return back({"error": "invalid_request",
                         "error_description": "code_challenge_method must be S256", **iss})

    code = secrets.token_urlsafe(16)
    CODES[code] = {"client_id": client_id, "user": "asha", "redirect_uri": redirect_uri,
                   "redirect_uri_sent": sent_redirect_uri is not None,
                   "code_challenge": code_challenge,
                   "method": code_challenge_method or "plain"}
    return back({"code": code, **iss})


def pkce_ok(details, verifier):
    if details["code_challenge"] is None:
        return True                        # PKCE was not used (only possible under 2.0)
    if verifier is None:
        return False
    if details["method"] == "S256":
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode() == details["code_challenge"]
    return verifier == details["code_challenge"]   # "plain", 2.0 only


@app.post("/token")
def token(grant_type: str = Form(...), client_id: str = Form(...),
          code: str | None = Form(None), code_verifier: str | None = Form(None),
          redirect_uri: str | None = Form(None), refresh_token: str | None = Form(None),
          username: str | None = Form(None), password: str | None = Form(None)):
    if client_id not in CLIENTS:
        return error("invalid_client", "unknown client", 401)

    if grant_type == "password":
        if PROFILE == "2.1":
            return error("unsupported_grant_type", "the password grant is not part of OAuth 2.1")
        if USERS.get(username) != password:
            return error("invalid_grant", "wrong username or password")
        return issue_tokens(username)

    if grant_type == "authorization_code":
        details = CODES.pop(code, None)
        if details is None or details["client_id"] != client_id:
            return error("invalid_grant", "unknown or used authorization code")
        if (PROFILE == "2.0" and details["redirect_uri_sent"]
                and redirect_uri != details["redirect_uri"]):
            return error("invalid_grant", "redirect_uri must match the authorization request")
        if not pkce_ok(details, code_verifier):
            return error("invalid_grant", "code_verifier does not match code_challenge")
        return issue_tokens(details["user"])

    if grant_type == "refresh_token":
        rt = REFRESH_TOKENS.get(refresh_token)
        if rt is None or rt["family"] in REVOKED_FAMILIES:
            return error("invalid_grant", "unknown or revoked refresh token")
        if PROFILE == "2.0":
            access = secrets.token_urlsafe(16)          # same refresh token stays valid
            ACCESS_TOKENS[access] = rt["user"]
            return {"access_token": access, "token_type": "Bearer", "expires_in": 600,
                    "scope": "books:read"}
        if not rt["active"]:
            # A rotated token came back: someone is replaying it. Revoke the whole family.
            REVOKED_FAMILIES.add(rt["family"])
            return error("invalid_grant", "refresh token reuse detected, grant revoked")
        rt["active"] = False                            # rotate: one-time use
        return issue_tokens(rt["user"], family=rt["family"])

    return error("unsupported_grant_type", f"grant_type {grant_type} is not supported")


@app.get("/books")
def books(request: Request):
    auth = request.headers.get("authorization", "")
    tok = auth[7:] if auth.lower().startswith("bearer ") else None
    if tok is None and PROFILE == "2.0":
        tok = request.query_params.get("access_token")  # RFC 6750 section 2.3
    if tok not in ACCESS_TOKENS:
        return JSONResponse({"error": "invalid_token"}, status_code=401,
                            headers={"WWW-Authenticate": 'Bearer realm="bookstore"'})
    return {"user": ACCESS_TOKENS[tok], "books": ["RESTful Web APIs", "Designing Web APIs"]}
