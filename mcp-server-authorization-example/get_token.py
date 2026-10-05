"""Gets an access token with the authorization code flow and PKCE, step by step.

Usage: python get_token.py <resource> <scope>
Prints the access token on stdout and its decoded claims on stderr.
"""

import base64
import hashlib
import json
import secrets
import sys
from urllib.parse import parse_qs, urlparse

import httpx2
import jwt

AUTH_SERVER = "http://127.0.0.1:9420"
CLIENT_ID = "orders-desktop"
REDIRECT_URI = "http://127.0.0.1:9499/callback"

resource, scope = sys.argv[1], sys.argv[2]

metadata = httpx2.get(f"{AUTH_SERVER}/.well-known/oauth-authorization-server").json()
if metadata["issuer"] != AUTH_SERVER:
    sys.exit("issuer in metadata does not match the authorization server URL")
if "S256" not in metadata.get("code_challenge_methods_supported", []):
    sys.exit("authorization server does not support PKCE with S256")

# PKCE: a random code_verifier, and its SHA-256 hash as the code_challenge.
code_verifier = secrets.token_urlsafe(48)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode("ascii")).digest()
).rstrip(b"=").decode("ascii")
state = secrets.token_urlsafe(16)

authorize_response = httpx2.get(metadata["authorization_endpoint"], params={
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": scope,
    "resource": resource,
    "state": state,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
})
callback = parse_qs(urlparse(authorize_response.headers["location"]).query)
if callback.get("state") != [state] or callback.get("iss") != [metadata["issuer"]]:
    sys.exit("state or iss in the redirect does not match")

token_response = httpx2.post(metadata["token_endpoint"], data={
    "grant_type": "authorization_code",
    "code": callback["code"][0],
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "code_verifier": code_verifier,
    "resource": resource,
})
access_token = token_response.json()["access_token"]

claims = jwt.decode(access_token, options={"verify_signature": False})  # display only
print(json.dumps(claims, indent=2), file=sys.stderr)
print(access_token)
