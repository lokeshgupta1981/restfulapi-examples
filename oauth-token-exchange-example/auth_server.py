"""DEMO authorization server with OAuth 2.0 Token Exchange (RFC 8693).

For learning only: clients, keys and policies live in memory, and the demo
user "asha" is signed in without a password. Use a real authorization server
(Keycloak, Auth0, Okta, Microsoft Entra ID, ...) in production.

Run: uvicorn auth_server:app --port 8000
"""
import base64
import os
import secrets
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse

ISSUER = os.environ.get("AUTH_URL", "http://127.0.0.1:8000")
TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KEY_ID = "demo-" + secrets.token_hex(4)

# Registered clients. The secrets are fake demo values.
CLIENTS = {
    "orders-api": {"secret": "demo-secret-orders-api"},
    "payments-api": {"secret": "demo-secret-payments-api"},
    "reports-api": {"secret": "demo-secret-reports-api"},
}

# Token exchange policy: which tokens a client may exchange (the audience the
# subject token was issued for) and which targets and scopes it may get.
EXCHANGE_POLICY = {
    "orders-api": {"accepts_audience": "orders-api",
                   "targets": {"payments-api": {"payments:charge"}},
                   "may_impersonate": True},
    "payments-api": {"accepts_audience": "payments-api",
                     "targets": {"ledger-api": {"ledger:write"}},
                     "may_impersonate": False},
    # Allowed here so the demo can show the Payments API refusing this actor.
    "reports-api": {"accepts_audience": "reports-api",
                    "targets": {"payments-api": {"payments:charge"}},
                    "may_impersonate": False},
}

# "resource" values (URLs) the server knows, mapped to logical audiences.
RESOURCES = {os.environ.get("PAYMENTS_URL", "http://127.0.0.1:8002"): "payments-api"}

STATS = {"exchanges": 0}

app = FastAPI(title="Demo authorization server (RFC 8693)")


def oauth_error(error, description, status=400):
    return JSONResponse({"error": error, "error_description": description},
                        status_code=status, headers={"Cache-Control": "no-store"})


def authenticate_client(request):
    """HTTP Basic client authentication (client_secret_basic)."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        return None
    try:
        client_id, _, secret = base64.b64decode(header[6:]).decode().partition(":")
    except ValueError:
        return None
    client = CLIENTS.get(client_id)
    if client and secrets.compare_digest(client["secret"], secret):
        return client_id
    return None


def issue(sub, aud, scope, lifetime, client_id, extra=None):
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": sub, "aud": aud, "scope": scope,
              "client_id": client_id, "iat": now, "exp": now + lifetime,
              "jti": str(uuid.uuid4())}
    claims.update(extra or {})
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256",
                      headers={"kid": KEY_ID, "typ": "at+jwt"})


def read_own_token(token, audience=None):
    """Validate a token this server issued. Raises jwt.InvalidTokenError."""
    return jwt.decode(token, PRIVATE_KEY.public_key(), algorithms=["RS256"],
                      issuer=ISSUER, audience=audience,
                      options={"verify_aud": audience is not None})


@app.get("/jwks")
def jwks():
    public = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
    public.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})
    return {"keys": [public]}


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    return {"issuer": ISSUER, "token_endpoint": ISSUER + "/token",
            "jwks_uri": ISSUER + "/jwks",
            "grant_types_supported": ["client_credentials", TOKEN_EXCHANGE],
            "token_endpoint_auth_methods_supported": ["client_secret_basic"]}


@app.post("/demo/login")
def demo_login(user: str = Form("asha"), aud: str = Form("orders-api")):
    """DEMO ONLY: stands in for the login flow of the bookstore web app.
    The user token is for one API only (the Orders API by default)."""
    scope = "orders:read orders:write" if aud == "orders-api" else "reports:read"
    token = issue(user, aud, scope, 900, "bookstore-web")
    return {"access_token": token, "token_type": "Bearer", "expires_in": 900}


@app.get("/demo/stats")
def demo_stats():
    return STATS


@app.post("/token")
def token(request: Request,
          grant_type: str = Form(...),
          scope: str = Form(""),
          audience: str | None = Form(None),
          resource: str | None = Form(None),
          requested_token_type: str | None = Form(None),
          subject_token: str | None = Form(None),
          subject_token_type: str | None = Form(None),
          actor_token: str | None = Form(None),
          actor_token_type: str | None = Form(None)):
    client_id = authenticate_client(request)
    if client_id is None:
        return oauth_error("invalid_client", "client authentication failed", 401)

    if grant_type == "client_credentials":
        # The service's own identity token. Used below as an actor_token.
        token = issue(client_id, ISSUER, "", 300, client_id)
        return JSONResponse({"access_token": token, "token_type": "Bearer",
                             "expires_in": 300}, headers={"Cache-Control": "no-store"})

    if grant_type != TOKEN_EXCHANGE:
        return oauth_error("unsupported_grant_type", grant_type)

    policy = EXCHANGE_POLICY.get(client_id)
    if policy is None:
        return oauth_error("unauthorized_client", "client may not exchange tokens")

    # 1. The subject token: who the new token is about.
    if not subject_token or subject_token_type != ACCESS_TOKEN:
        return oauth_error("invalid_request", "subject_token must be an access token")
    try:
        subject = read_own_token(subject_token, audience=policy["accepts_audience"])
    except jwt.InvalidTokenError as exc:
        return oauth_error("invalid_request", f"subject_token rejected: {exc}")

    # 2. The actor token (optional): who will act. Must be the caller itself.
    if (actor_token is None) != (actor_token_type is None):
        return oauth_error("invalid_request", "send actor_token and actor_token_type together")
    actor = None
    if actor_token:
        if actor_token_type != ACCESS_TOKEN:
            return oauth_error("invalid_request", "unsupported actor_token_type")
        try:
            actor = read_own_token(actor_token, audience=ISSUER)
        except jwt.InvalidTokenError as exc:
            return oauth_error("invalid_request", f"actor_token rejected: {exc}")
        if actor["sub"] != client_id:
            return oauth_error("invalid_request", "actor_token does not belong to the client")
    elif not policy["may_impersonate"]:
        return oauth_error("invalid_request", "this client must send an actor_token")

    # 3. The target: where the new token will be used.
    target = audience or RESOURCES.get(resource or "")
    if target not in policy["targets"]:
        return oauth_error("invalid_target", f"{client_id} may not get tokens for {audience or resource}")
    if requested_token_type not in (None, ACCESS_TOKEN):
        return oauth_error("invalid_request", "only access tokens can be issued")

    # 4. The scope: never more than the policy allows for this target.
    requested = set(scope.split())
    allowed = policy["targets"][target]
    if not requested or not requested <= allowed:
        return oauth_error("invalid_scope", f"allowed scopes: {' '.join(sorted(allowed))}")

    # 5. Delegation adds an act claim; earlier actors are nested inside it.
    extra = {}
    if actor:
        act = {"sub": client_id}
        if "act" in subject:
            act["act"] = subject["act"]
        extra["act"] = act

    # The new token never outlives the token it came from.
    lifetime = max(0, min(300, subject["exp"] - int(time.time())))
    new_token = issue(subject["sub"], target, " ".join(sorted(requested)), lifetime,
                      client_id, extra)
    STATS["exchanges"] += 1
    return JSONResponse({"access_token": new_token,
                         "issued_token_type": ACCESS_TOKEN,
                         "token_type": "Bearer",
                         "expires_in": lifetime,
                         "scope": " ".join(sorted(requested))},
                        headers={"Cache-Control": "no-store"})
