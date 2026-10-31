"""Demo authorization server that accepts both kinds of client registration.

- Dynamic Client Registration (RFC 7591): POST /register stores a new client.
- Client ID Metadata Documents (draft-ietf-oauth-client-id-metadata-document-02):
  a client_id that is an https URL is fetched, validated and cached.

Authorization code flow with PKCE (S256) for public clients only.
Demo only: there is no login or consent page, the user is always signed in
and always approves, and everything lives in memory.
"""

import base64
import hashlib
import ipaddress
import os
import re
import secrets
import socket
import time
from urllib.parse import urlencode, urlsplit

import httpx
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

PORT = int(os.environ.get("AS_PORT", "9000"))
ISSUER = os.environ.get("AS_ISSUER", f"http://127.0.0.1:{PORT}")

# Development only: allow client_id URLs that resolve to a loopback address.
# The draft forbids this exception in production (Section 8.6).
ALLOW_LOOPBACK = os.environ.get("CIMD_ALLOW_LOOPBACK") == "1"
# CA file used to verify the client's https certificate (our self-signed dev cert).
CA_FILE = os.environ.get("CIMD_CA_FILE") or True

MAX_DOCUMENT_BYTES = 5 * 1024          # draft Section 8.7 recommends 5 KB
DEFAULT_CACHE_SECONDS = 300            # used when the document sends no max-age
MAX_CACHE_SECONDS = 24 * 3600          # our own upper bound
SHARED_SECRET_METHODS = {"client_secret_post", "client_secret_basic", "client_secret_jwt"}

app = FastAPI()

registered_clients: dict[str, dict] = {}   # DCR: one record per POST /register
cimd_cache: dict[str, tuple[dict, float]] = {}  # CIMD: url -> (document, expires_at)
stats = {"cimd_fetches": 0}
pending_codes: dict[str, dict] = {}


class ClientError(Exception):
    def __init__(self, error: str, description: str):
        self.error, self.description = error, description


def error_response(error: str, description: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": error, "error_description": description}, status_code=status)


@app.get("/.well-known/oauth-authorization-server")
def metadata():
    """RFC 8414 metadata. It advertises both registration options."""
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "registration_endpoint": f"{ISSUER}/register",
        "client_id_metadata_document_supported": True,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "authorization_response_iss_parameter_supported": True,
    }


def valid_redirect_uri(uri: str) -> bool:
    parts = urlsplit(uri)
    if parts.fragment:
        return False
    if parts.scheme == "https":
        return True
    return parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost", "::1")


# ---------------------------------------------------------------- DCR (RFC 7591)

@app.post("/register")
async def register(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return error_response("invalid_client_metadata", "Body must be JSON")
    redirect_uris = body.get("redirect_uris")
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return error_response("invalid_redirect_uri", "redirect_uris is required")
    if not all(isinstance(u, str) and valid_redirect_uri(u) for u in redirect_uris):
        return error_response("invalid_redirect_uri", "Redirect URIs must use https or a loopback http address")
    if body.get("token_endpoint_auth_method", "none") != "none":
        return error_response("invalid_client_metadata", "This server only registers public clients (none)")

    client_id = "dcr_" + secrets.token_urlsafe(12)
    client = {
        "client_id": client_id,
        "client_id_issued_at": int(time.time()),
        "client_name": body.get("client_name", client_id),
        "redirect_uris": redirect_uris,
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    registered_clients[client_id] = client
    print(f"[dcr] registered {client_id} as {client['client_name']!r} "
          f"({len(registered_clients)} registrations stored)", flush=True)
    return JSONResponse(client, status_code=201)


# ---------------------------------------------------------------- CIMD

def check_client_id_url(url: str) -> None:
    """Section 3 rules for a Client Identifier URL."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise ClientError("invalid_client", "client_id URL must use https")
    if parts.username or parts.password:
        raise ClientError("invalid_client", "client_id URL must not contain user info")
    if parts.fragment:
        raise ClientError("invalid_client", "client_id URL must not contain a fragment")
    if not parts.path or parts.path == "/":
        raise ClientError("invalid_client", "client_id URL must contain a path")
    if any(seg in (".", "..") for seg in parts.path.split("/")):
        raise ClientError("invalid_client", "client_id URL must not contain . or .. segments")


def check_address(host: str, port: int) -> None:
    """SSRF guard (Section 8.6): never fetch special-use addresses."""
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ClientError("invalid_client", f"cannot resolve {host}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_loopback and ALLOW_LOOPBACK:
            continue
        if not ip.is_global:
            raise ClientError("invalid_client", f"{host} resolves to {ip}, a non-public address; not fetched")


def max_age(cache_control: str | None) -> int:
    match = re.search(r"max-age=(\d+)", cache_control or "")
    seconds = int(match.group(1)) if match else DEFAULT_CACHE_SECONDS
    if "no-store" in (cache_control or ""):
        seconds = 0
    return min(seconds, MAX_CACHE_SECONDS)


def resolve_cimd_client(url: str) -> dict:
    cached = cimd_cache.get(url)
    if cached and cached[1] > time.time():
        return cached[0]

    check_client_id_url(url)
    parts = urlsplit(url)
    check_address(parts.hostname, parts.port or 443)

    stats["cimd_fetches"] += 1
    try:
        with httpx.Client(verify=CA_FILE, follow_redirects=False, timeout=3.0) as http:
            with http.stream("GET", url, headers={"Accept": "application/json"}) as resp:
                if resp.status_code != 200:
                    note = " (redirects are not followed)" if resp.is_redirect else ""
                    raise ClientError("invalid_client", f"metadata document returned HTTP {resp.status_code}{note}")
                body = b""
                for chunk in resp.iter_bytes():
                    body += chunk
                    if len(body) > MAX_DOCUMENT_BYTES:
                        raise ClientError("invalid_client", f"metadata document is larger than {MAX_DOCUMENT_BYTES} bytes")
                cache_control = resp.headers.get("cache-control")
    except httpx.HTTPError as exc:
        raise ClientError("invalid_client", f"cannot fetch metadata document: {exc.__class__.__name__}")

    try:
        doc = httpx.Response(200, content=body).json()
    except ValueError:
        raise ClientError("invalid_client", "metadata document is not valid JSON")
    if not isinstance(doc, dict):
        raise ClientError("invalid_client", "metadata document must be a JSON object")
    if doc.get("client_id") != url:
        raise ClientError("invalid_client", f"client_id in document ({doc.get('client_id')}) does not match the URL")
    for field in ("client_name", "redirect_uris"):
        if not doc.get(field):
            raise ClientError("invalid_client", f"metadata document has no {field}")
    if "client_secret" in doc or "client_secret_expires_at" in doc:
        raise ClientError("invalid_client", "metadata document must not contain a client secret")
    if doc.get("token_endpoint_auth_method") in SHARED_SECRET_METHODS:
        raise ClientError("invalid_client", "shared-secret authentication is not allowed for these clients")

    seconds = max_age(cache_control)
    if seconds > 0:
        cimd_cache[url] = (doc, time.time() + seconds)
    print(f"[cimd] fetched {url} ({len(body)} bytes), cached for {seconds} s", flush=True)
    return doc


def find_client(client_id: str) -> dict:
    if "://" in client_id:
        return resolve_cimd_client(client_id)
    client = registered_clients.get(client_id)
    if client is None:
        raise ClientError("invalid_client", "unknown client_id")
    return client


# ---------------------------------------------------------------- OAuth endpoints

@app.get("/authorize")
def authorize(client_id: str, redirect_uri: str, response_type: str = "code",
              code_challenge: str = "", code_challenge_method: str = "", state: str = ""):
    # Errors before the redirect URI is verified are shown here, never redirected.
    try:
        client = find_client(client_id)
    except ClientError as exc:
        return error_response(exc.error, exc.description)
    if redirect_uri not in client["redirect_uris"]:
        return error_response("invalid_request", "redirect_uri is not registered for this client")
    if response_type != "code" or code_challenge_method != "S256" or not code_challenge:
        return error_response("invalid_request", "response_type=code and PKCE with S256 are required")

    # A real server shows a consent page here. We show what it would display.
    shown = f"{client['client_name']} (client from {urlsplit(client_id).hostname or 'registration'}, " \
            f"redirects to {urlsplit(redirect_uri).hostname})"
    code = secrets.token_urlsafe(24)
    pending_codes[code] = {"client_id": client_id, "redirect_uri": redirect_uri,
                           "code_challenge": code_challenge, "expires_at": time.time() + 60}
    query = urlencode({"code": code, "state": state, "iss": ISSUER})
    return RedirectResponse(f"{redirect_uri}?{query}", status_code=302,
                            headers={"X-Demo-Consent-Screen": shown})


@app.post("/token")
def token(grant_type: str = Form(...), code: str = Form(...), redirect_uri: str = Form(...),
          client_id: str = Form(...), code_verifier: str = Form(...)):
    entry = pending_codes.pop(code, None)
    if grant_type != "authorization_code" or entry is None or entry["expires_at"] < time.time():
        return error_response("invalid_grant", "unknown or expired code")
    if entry["client_id"] != client_id or entry["redirect_uri"] != redirect_uri:
        return error_response("invalid_grant", "code was issued to another client or redirect_uri")
    digest = hashlib.sha256(code_verifier.encode()).digest()
    if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != entry["code_challenge"]:
        return error_response("invalid_grant", "PKCE verification failed")
    return {"access_token": secrets.token_urlsafe(32), "token_type": "Bearer", "expires_in": 600}


@app.get("/demo/stats")
def demo_stats():
    """What the server had to store or do so far (demo endpoint)."""
    return {
        "dcr_registrations_stored": len(registered_clients),
        "cimd_documents_cached": len(cimd_cache),
        "cimd_fetches": stats["cimd_fetches"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
