"""A public OAuth client (think: an MCP client app) that gets a client_id
the way the MCP 2026-07-28 spec recommends:

  1. pre-registered client_id, if we have one for this issuer
  2. Client ID Metadata Document, if the server supports it
  3. Dynamic Client Registration, if the server has a registration_endpoint

Then it runs the authorization code flow with PKCE.

Usage: python client.py AS_URL [auto|cimd|dcr]
"""

import base64
import hashlib
import json
import os
import secrets
import sys
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

CLIENT_METADATA_URL = os.environ.get("CLIENT_METADATA_URL", "https://localhost:8443/oauth/client-metadata.json")
CALLBACK = os.environ.get("CLIENT_CALLBACK", "http://127.0.0.1:8765/callback")
PRE_REGISTERED = {}  # issuer -> client_id, filled from configuration in a real app
STORE = "dcr_registrations.json"


def load_store() -> dict:
    try:
        with open(STORE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def register_with_dcr(http: httpx.Client, meta: dict) -> str:
    store = load_store()
    issuer = meta["issuer"]
    if issuer in store:                      # credentials are bound to the issuer
        print(f"   reusing stored registration for {issuer}")
        return store[issuer]["client_id"]
    resp = http.post(meta["registration_endpoint"], json={
        "client_name": "Orders Desktop",
        "redirect_uris": [CALLBACK],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "application_type": "native",
    })
    print(f"   POST {meta['registration_endpoint']} -> HTTP {resp.status_code}")
    resp.raise_for_status()
    store[issuer] = resp.json()
    with open(STORE, "w") as f:
        json.dump(store, f, indent=2)
    return store[issuer]["client_id"]


def choose_client_id(http: httpx.Client, meta: dict, mode: str) -> str:
    issuer = meta["issuer"]
    if mode == "auto" and issuer in PRE_REGISTERED:
        print("2. Using the pre-registered client_id")
        return PRE_REGISTERED[issuer]
    if mode in ("auto", "cimd") and meta.get("client_id_metadata_document_supported"):
        print("2. Server supports Client ID Metadata Documents: our URL is our client_id")
        return CLIENT_METADATA_URL
    if mode in ("auto", "dcr") and meta.get("registration_endpoint"):
        print("2. Falling back to Dynamic Client Registration")
        return register_with_dcr(http, meta)
    sys.exit("2. No way to get a client_id: ask the user to enter one")


def main() -> None:
    as_url = sys.argv[1].rstrip("/")
    mode = sys.argv[2] if len(sys.argv) > 2 else "auto"
    with httpx.Client(timeout=5.0) as http:
        meta = http.get(f"{as_url}/.well-known/oauth-authorization-server").json()
        print(f"1. Metadata: client_id_metadata_document_supported="
              f"{meta.get('client_id_metadata_document_supported', False)}, "
              f"registration_endpoint={'yes' if meta.get('registration_endpoint') else 'no'}")

        client_id = choose_client_id(http, meta, mode)
        print(f"   client_id = {client_id}")

        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        resp = http.get(meta["authorization_endpoint"] + "?" + urlencode({
            "response_type": "code", "client_id": client_id, "redirect_uri": CALLBACK,
            "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
        }))
        if resp.status_code != 302:
            sys.exit(f"3. Authorization failed: HTTP {resp.status_code} {resp.text}")
        print(f"3. Consent screen shows: {resp.headers['x-demo-consent-screen']}")
        params = parse_qs(urlsplit(resp.headers["location"]).query)
        assert params["state"][0] == state and params["iss"][0] == meta["issuer"]
        print(f"   redirected to {CALLBACK} with a code, state and iss checked")

        resp = http.post(meta["token_endpoint"], data={
            "grant_type": "authorization_code", "code": params["code"][0], "redirect_uri": CALLBACK,
            "client_id": client_id, "code_verifier": verifier,
        })
        token = resp.json()
        print(f"4. Token: HTTP {resp.status_code}, {token['token_type']} token, expires_in {token['expires_in']}")


if __name__ == "__main__":
    main()
