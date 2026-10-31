"""Shows what a JWT signature covers: build an HS256 token, take it apart, verify it by hand,
then tamper with the payload and verify again."""
import base64
import hashlib
import hmac
import json

import jwt

SECRET = bytes.fromhex("6b7f3c0e9a1d4e2f8b5a7c3d1e9f0a2b4c6d8e0f1a3b5c7d9e1f3a5b7c9d1e3f")  # demo key


def b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


claims = {"sub": "alice", "role": "customer", "iat": 1793350800, "exp": 1793351100}
token = jwt.encode(claims, SECRET, algorithm="HS256", headers={"kid": "hs-demo-1"})
print("== Token")
print(token)

header_b64, payload_b64, signature_b64 = token.split(".")
print("\n== The three parts")
print("header   :", b64url_decode(header_b64).decode())
print("payload  :", b64url_decode(payload_b64).decode())
print("signature:", signature_b64, f"({len(b64url_decode(signature_b64))} bytes)")

print("\n== Verify by hand: HMAC-SHA256(secret, header + '.' + payload)")
signing_input = f"{header_b64}.{payload_b64}".encode()
expected = b64url_encode(hmac.new(SECRET, signing_input, hashlib.sha256).digest())
print("computed :", expected)
print("matches  :", hmac.compare_digest(expected, signature_b64))

print("\n== Tamper: change role to admin, keep the old signature")
forged_payload = dict(claims, role="admin")
forged_b64 = b64url_encode(json.dumps(forged_payload, separators=(",", ":")).encode())
forged = f"{header_b64}.{forged_b64}.{signature_b64}"
print("payload  :", b64url_decode(forged_b64).decode())
try:
    jwt.decode(forged, SECRET, algorithms=["HS256"], options={"verify_exp": False})
except jwt.InvalidSignatureError as exc:
    print("PyJWT    :", type(exc).__name__, "-", exc)
