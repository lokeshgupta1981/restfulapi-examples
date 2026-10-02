"""DEMO authorization server for learning only.

It has no login page, keeps clients and keys in memory and signs in the demo
user "asha" automatically. In production, use a real authorization server such
as Keycloak, Auth0, Okta or Microsoft Entra ID.

Run: uvicorn auth_server:app --port 9200
"""
import base64
import hashlib
import secrets
import time
import uuid
from urllib.parse import urlencode

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

ISSUER = "http://127.0.0.1:9200"
ORDERS_API = "http://127.0.0.1:9201"
TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"

# A new RSA key pair and key id on every start. Real servers store their keys
# and rotate them; a new "kid" tells APIs to fetch the JWKS again.
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KEY_ID = "demo-" + secrets.token_hex(4)

# Registered clients. The secrets are fake demo values.
CLIENTS = {
    # A nightly bot that acts for itself (client credentials). It may read
    # every customer's orders, so it gets the extra scope orders:read:all.
    "report-bot": {"secret": "demo-secret-report-bot", "grants": {"client_credentials"},
                   "scopes": {"orders:read", "orders:read:all"}},
    # The chat app where the user signs in (public client, so PKCE, no secret).
    "chat-app": {"secret": None, "grants": {"authorization_code"},
                 "scopes": {"orders:read", "orders:write"},
                 "redirect_uri": "http://127.0.0.1:9299/callback"},
    # The AI agent that acts for the signed-in user (token exchange).
    "shop-assistant": {"secret": "demo-secret-shop-assistant",
                       "grants": {TOKEN_EXCHANGE},
                       "scopes": {"orders:read", "orders:write"}},
}
USER_SCOPES = {"asha": {"orders:read", "orders:write"}}
CODES = {}  # authorization code -> details, used once

app = FastAPI(title="Demo authorization server")


def oauth_error(error, description, status=400):
    return JSONResponse({"error": error, "error_description": description},
                        status_code=status, headers={"Cache-Control": "no-store"})


def client_ok(client, secret):
    # Public clients have no secret. Compare secrets in constant time.
    if client is None:
        return False
    if client["secret"] is None:
        return secret is None
    return secret is not None and secrets.compare_digest(client["secret"], secret)


def issue_token(sub, client_id, aud, scopes, lifetime, extra=None):
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": sub, "aud": aud, "client_id": client_id,
              "scope": " ".join(sorted(scopes)), "iat": now, "exp": now + lifetime,
              "jti": str(uuid.uuid4())}
    claims.update(extra or {})
    # RFC 9068: a JWT access token has the header typ "at+jwt".
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256",
                      headers={"kid": KEY_ID, "typ": "at+jwt"})


def token_response(token, scopes, lifetime, issued_type=None):
    body = {"access_token": token, "token_type": "Bearer",
            "expires_in": lifetime, "scope": " ".join(sorted(scopes))}
    if issued_type:
        body["issued_token_type"] = issued_type
    return JSONResponse(body, headers={"Cache-Control": "no-store"})


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    # RFC 8414 metadata: clients and APIs read the endpoints and keys from here.
    return {"issuer": ISSUER,
            "authorization_endpoint": ISSUER + "/authorize",
            "token_endpoint": ISSUER + "/token",
            "jwks_uri": ISSUER + "/jwks",
            "grant_types_supported": ["authorization_code", "client_credentials",
                                      TOKEN_EXCHANGE],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
            "scopes_supported": ["orders:read", "orders:read:all", "orders:write"]}


@app.get("/jwks")
def jwks():
    # Only the public key is published. APIs use it to check signatures.
    public = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
    public.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})
    return {"keys": [public]}


@app.get("/authorize")
def authorize(client_id: str, redirect_uri: str, scope: str, state: str,
              code_challenge: str, code_challenge_method: str = "S256"):
    client = CLIENTS.get(client_id)
    if not client or client.get("redirect_uri") != redirect_uri:
        return oauth_error("invalid_request", "unknown client or redirect_uri")
    if code_challenge_method != "S256":
        return oauth_error("invalid_request", "PKCE with S256 is required")
    # DEMO ONLY: a real server shows a login page and a consent screen here.
    user = "asha"
    code = secrets.token_urlsafe(24)
    CODES[code] = {"client_id": client_id, "redirect_uri": redirect_uri,
                   "user": user, "scopes": set(scope.split()) & USER_SCOPES[user],
                   "challenge": code_challenge, "expires": time.time() + 60}
    query = urlencode({"code": code, "state": state, "iss": ISSUER})
    return RedirectResponse(redirect_uri + "?" + query, status_code=302)


@app.post("/token")
def token(request: Request, grant_type: str = Form(...), client_id: str = Form(...),
          client_secret: str | None = Form(None), scope: str = Form(""),
          resource: str = Form(ORDERS_API), code: str | None = Form(None),
          redirect_uri: str | None = Form(None), code_verifier: str | None = Form(None),
          subject_token: str | None = Form(None),
          subject_token_type: str | None = Form(None)):
    client = CLIENTS.get(client_id)
    if not client_ok(client, client_secret):
        return oauth_error("invalid_client", "client authentication failed", 401)
    if grant_type not in client["grants"]:
        return oauth_error("unauthorized_client", "grant not allowed for this client")
    requested = set(scope.split())

    if grant_type == "client_credentials":
        # The agent acts for itself: sub is the client, no user involved.
        if resource != ORDERS_API:
            return oauth_error("invalid_target", "unknown resource")
        if not requested or not requested <= client["scopes"]:
            return oauth_error("invalid_scope", "scope not allowed for this client")
        return token_response(issue_token(client_id, client_id, resource, requested, 300),
                              requested, 300)

    if grant_type == "authorization_code":
        entry = CODES.pop(code or "", None)
        if not entry or entry["expires"] < time.time() or entry["client_id"] != client_id \
                or entry["redirect_uri"] != redirect_uri:
            return oauth_error("invalid_grant", "invalid or expired code")
        # PKCE check: SHA-256 of the verifier must match the challenge.
        digest = hashlib.sha256((code_verifier or "").encode()).digest()
        if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != entry["challenge"]:
            return oauth_error("invalid_grant", "PKCE verification failed")
        # The user token is for the agent only, and names who may act with it.
        extra = {"may_act": {"sub": "shop-assistant"}}
        token = issue_token(entry["user"], client_id, "shop-assistant",
                            entry["scopes"], 600, extra)
        return token_response(token, entry["scopes"], 600)

    # RFC 8693 token exchange: user token in, smaller agent token out.
    if subject_token_type != ACCESS_TOKEN_TYPE or not subject_token:
        return oauth_error("invalid_request", "subject_token must be an access token")
    try:
        subject = jwt.decode(subject_token, PRIVATE_KEY.public_key(), algorithms=["RS256"],
                             issuer=ISSUER, audience=client_id)
    except jwt.InvalidTokenError as exc:
        return oauth_error("invalid_request", f"subject_token rejected: {exc}")
    if subject.get("may_act", {}).get("sub") != client_id:
        return oauth_error("invalid_request", f"{client_id} may not act for this user")
    if resource != ORDERS_API:
        return oauth_error("invalid_target", "unknown resource")
    allowed = set(subject["scope"].split()) & client["scopes"]
    if not requested or not requested <= allowed:
        return oauth_error("invalid_scope", f"allowed scopes: {' '.join(sorted(allowed))}")
    # The act claim records the agent. Keep an earlier act claim as history.
    act = {"sub": client_id}
    if "act" in subject:
        act["act"] = subject["act"]
    # The agent token never lives longer than the user token it came from.
    lifetime = min(300, subject["exp"] - int(time.time()))
    token = issue_token(subject["sub"], client_id, resource, requested, lifetime, {"act": act})
    return token_response(token, requested, lifetime, ACCESS_TOKEN_TYPE)
