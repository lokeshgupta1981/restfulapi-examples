"""Builds the demo HS256 JWT that all three servers accept on /bearer/orders.

The key is a public demo value for local tests, never a real secret.
"""
import base64
import hashlib
import hmac
import json

DEMO_KEY = b"demo-secret-key-123-only-for-local-tests"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
claims = b64url(json.dumps({"sub": "reports-app", "scope": "orders.read", "exp": 1924992000},
                           separators=(",", ":")).encode())
signature = b64url(hmac.new(DEMO_KEY, f"{header}.{claims}".encode(), hashlib.sha256).digest())
print(f"{header}.{claims}.{signature}")
