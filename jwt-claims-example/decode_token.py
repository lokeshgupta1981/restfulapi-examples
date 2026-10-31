"""Split a JWT and Base64URL-decode its parts WITHOUT any library or key.

Shows that claims are readable by anyone who holds the token.
Usage: python decode_token.py tokens/valid.jwt
"""
import base64
import json
import sys
from datetime import datetime, timezone


def b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


token = open(sys.argv[1]).read().strip()
header, payload, signature = token.split(".")
print("Token length:", len(token), "characters")
print("Header: ", json.dumps(json.loads(b64url_decode(header))))
claims = json.loads(b64url_decode(payload))
print("Payload:", json.dumps(claims, indent=2))
for name in ("iat", "nbf", "exp"):
    if name in claims:
        print(f"{name} {claims[name]} = {datetime.fromtimestamp(claims[name], timezone.utc).isoformat()}")
print("Signature:", len(b64url_decode(signature)), "bytes")
