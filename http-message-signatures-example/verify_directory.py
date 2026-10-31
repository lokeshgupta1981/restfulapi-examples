"""Verifies a real, signed key directory: the one ChatGPT agent publishes.

By default it checks the snapshot captured on 2026-10-31 in snapshots/.
Run with --live to fetch https://chatgpt.com/.well-known/http-message-signatures-directory now.

Checks:
1. Content-Digest matches the SHA-256 of the body bytes
2. Each key's kid equals its JWK thumbprint
3. The response signature (tag "http-message-signatures-directory") verifies
   with the key from the directory itself, over "@authority";req and content-digest
"""
import json
import sys

import httpx

from httpsig import (Message, SignatureError, content_digest, jwk_thumbprint,
                     parse_signatures, public_key_from_jwk, verify)

URL = "https://chatgpt.com/.well-known/http-message-signatures-directory"

if "--live" in sys.argv:
    r = httpx.get(URL, headers={"Accept": "application/http-message-signatures-directory+json"},
                  timeout=10, follow_redirects=False)
    snap = {"url": URL, "status": r.status_code, "headers": dict(r.headers), "body": r.text}
    print("fetched live at", r.headers.get("date"))
else:
    with open("snapshots/chatgpt-directory-2026-10-31.json") as f:
        snap = json.load(f)
    print("snapshot captured at", snap["headers"]["date"])

body = snap["body"].encode()
directory = json.loads(body)
print("status:", snap["status"], "| content-type:", snap["headers"]["content-type"])
print("keys in directory:", len(directory["keys"]))

print("1. content-digest matches body:", snap["headers"]["content-digest"] == content_digest(body))

keys = {}
for jwk in directory["keys"]:
    thumb = jwk_thumbprint(jwk)
    print("2. kid", jwk["kid"], "equals thumbprint:", jwk["kid"] == thumb)
    keys[thumb] = jwk

request = Message(method="GET", url=snap["url"])
response = Message(status=snap["status"], headers=snap["headers"], request=request)
for label, (covered, sig) in parse_signatures(response).items():
    params = covered.params
    print(f"3. signature {label}: tag={params['tag']} created={params['created']} expires={params['expires']}")
    jwk = keys.get(params["keyid"])
    try:
        base = verify(response, covered, sig, public_key_from_jwk(jwk))
        print("   signature base:")
        print("   " + base.replace("\n", "\n   "))
        print("   result: valid")
    except SignatureError as e:
        print("   result: INVALID", e)
