"""Demo token issuer for the Orders API.

Creates an RSA demo key pair on first use (stored in demo-keys/, never commit it)
and signs JWT access tokens with RS256. Every claim can be overridden or removed,
so the demo can produce valid and broken tokens.
"""
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://auth.bookstore.example"
AUDIENCE = "https://api.bookstore.example/orders"
KEY_DIR = Path(__file__).parent / "demo-keys"
KID = "demo-key-1"


def _load_or_create_private_key():
    KEY_DIR.mkdir(exist_ok=True)
    pem_file = KEY_DIR / "demo-private-key.pem"
    if not pem_file.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem_file.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        (KEY_DIR / "demo-public-key.pem").write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    return serialization.load_pem_private_key(pem_file.read_bytes(), password=None)


PRIVATE_KEY = _load_or_create_private_key()
PUBLIC_KEY = PRIVATE_KEY.public_key()


def base_claims(now=None):
    now = int(now or time.time())
    return {
        # registered claims (RFC 7519)
        "iss": ISSUER,
        "sub": "user-4711",
        "aud": AUDIENCE,
        "exp": now + 300,
        "nbf": now,
        "iat": now,
        "jti": str(uuid.uuid4()),
        # registered in the IANA registry by other RFCs
        "client_id": "bookstore-web",
        "scope": "orders:read orders:write",
        # public claim: collision-resistant name (a URL we control)
        "https://bookstore.example/claims/tenant": "acme-books",
        # private claim: short name agreed between our issuer and our API
        "plan": "pro",
    }


def make_token(drop=(), key=None, headers=None, **overrides):
    """Return a signed JWT. drop removes claims, overrides replaces or adds them."""
    claims = base_claims()
    claims.update(overrides)
    for name in drop:
        claims.pop(name, None)
    hdr = {"kid": KID, "typ": "at+jwt"}
    hdr.update(headers or {})
    return jwt.encode(claims, key or PRIVATE_KEY, algorithm="RS256", headers=hdr)
