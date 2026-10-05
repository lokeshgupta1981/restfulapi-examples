"""Shipments API that answers failed authentication with WWW-Authenticate challenges.

The tokens and the password below are fake demo values. Never put real secrets in code.
"""
import base64
import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

PORT = int(os.environ.get("PORT", "9420"))
BASE_URL = "http://127.0.0.1:" + str(PORT)
REALM = "shipments-api"
RESOURCE = BASE_URL + "/shipments"
# RFC 9728 section 3.1: the well-known suffix goes between the host and the resource path.
METADATA_URL = BASE_URL + "/.well-known/oauth-protected-resource/shipments"

# Demo tokens: value -> granted scopes (None means the token has expired).
DEMO_TOKENS = {
    "demo-token-read": {"shipments:read"},
    "demo-token-expired": None,
}
# Demo Basic credentials for the legacy endpoint.
DEMO_USER = "ana"
DEMO_PASSWORD = "demo-pass-123"

app = FastAPI()

# EXPOSE=0 starts a second copy that does not expose the header to browser scripts.
if os.environ.get("EXPOSE", "1") == "1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:9421"],
        allow_headers=["Authorization"],
        expose_headers=["WWW-Authenticate"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:9421"],
        allow_headers=["Authorization"],
    )


class AuthError(Exception):
    def __init__(self, status, error=None, description=None, scope=None):
        self.status = status
        self.error = error
        self.description = description
        self.scope = scope


def quoted(value):
    """Wrap a value in double quotes. RFC 6750 forbids " and \\ in these values."""
    if '"' in value or "\\" in value:
        raise ValueError("A challenge value must not contain a double quote or a backslash")
    return '"' + value + '"'


def bearer_challenge(error=None, description=None, scope=None):
    """Build one Bearer challenge. RFC 6750: no error code when no token was sent."""
    params = ["realm=" + quoted(REALM)]
    if error:
        params.append("error=" + quoted(error))
    if description:
        params.append("error_description=" + quoted(description))
    if scope:
        params.append("scope=" + quoted(scope))
    params.append("resource_metadata=" + quoted(METADATA_URL))
    return "Bearer " + ", ".join(params)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    body = {"status": exc.status, "error": exc.error or "unauthorized"}
    if exc.description:
        body["detail"] = exc.description
    challenge = bearer_challenge(exc.error, exc.description, exc.scope)
    return JSONResponse(body, status_code=exc.status,
                        headers={"WWW-Authenticate": challenge})


def require_scope(scope):
    def check(request: Request):
        values = request.headers.getlist("authorization")
        if not values:
            raise AuthError(401)
        if len(values) > 1:
            raise AuthError(400, "invalid_request", "Send one Authorization header")
        parts = values[0].split(" ")
        if parts[0].lower() != "bearer":
            # Unsupported scheme: answer like a missing token, without an error code.
            raise AuthError(401)
        if len(parts) != 2 or not parts[1]:
            raise AuthError(400, "invalid_request", "Malformed Bearer credentials")
        token = parts[1]
        if token not in DEMO_TOKENS:
            raise AuthError(401, "invalid_token", "Unknown token")
        scopes = DEMO_TOKENS[token]
        if scopes is None:
            raise AuthError(401, "invalid_token", "The access token expired")
        if scope not in scopes:
            raise AuthError(403, "insufficient_scope", "Token lacks " + scope, scope)
        return token
    return check


@app.get("/shipments")
def list_shipments(token: str = Depends(require_scope("shipments:read"))):
    return [{"id": "shp_1001", "status": "in_transit"}]


@app.post("/shipments", status_code=201)
def create_shipment(token: str = Depends(require_scope("shipments:write"))):
    return {"id": "shp_1002", "status": "created"}


@app.get("/.well-known/oauth-protected-resource/shipments")
def resource_metadata():
    # RFC 9728 protected resource metadata. The authorization server is a demo URL.
    return {
        "resource": RESOURCE,
        "authorization_servers": ["https://auth.example.com"],
        "scopes_supported": ["shipments:read", "shipments:write"],
        "bearer_methods_supported": ["header"],
    }


@app.get("/v2/shipments")
def list_shipments_v2(request: Request):
    # Accepts Bearer or DPoP tokens, so it sends two challenges as two header lines.
    if request.headers.get("authorization") == "Bearer demo-token-read":
        return [{"id": "shp_1001", "status": "in_transit"}]
    response = JSONResponse({"status": 401, "error": "unauthorized"}, status_code=401)
    response.headers.append("WWW-Authenticate", 'Bearer realm="' + REALM + '"')
    response.headers.append("WWW-Authenticate", 'DPoP algs="ES256 PS256"')
    return response


@app.get("/legacy/reports")
def legacy_reports(request: Request):
    # Basic authentication: the challenge that makes browsers show a login dialog.
    header = request.headers.get("authorization", "")
    if header.startswith("Basic "):
        user_pass = base64.b64decode(header[6:]).decode("utf-8")
        if user_pass == DEMO_USER + ":" + DEMO_PASSWORD:
            return {"report": "monthly-shipments", "rows": 42}
    return JSONResponse(
        {"status": 401, "error": "unauthorized"}, status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="legacy-reports", charset="UTF-8"'},
    )


bearer_scheme = HTTPBearer()


@app.get("/builtin")
def builtin(credentials=Depends(bearer_scheme)):
    # FastAPI's own HTTPBearer, to compare its challenge with ours.
    return {"scheme": credentials.scheme}


@app.get("/", include_in_schema=False)
def page():
    # Same-origin page used by browser_check.py.
    from fastapi.responses import HTMLResponse
    return HTMLResponse("<!doctype html><title>same origin</title><p>ok</p>")
