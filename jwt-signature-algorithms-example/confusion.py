"""alg=none and algorithm confusion: a naive verifier that trusts the token's "alg" header
accepts two forged tokens. PyJWT with a pinned algorithm rejects both."""
import base64
import hashlib
import hmac
import json
import time

import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_PEM = rsa_key.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo)


def b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64d(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def naive_verify(token: str, key: bytes) -> dict:
    """DON'T DO THIS: the token's own header decides how it is checked."""
    h, p, s = token.split(".")
    alg = json.loads(b64d(h))["alg"]
    signing_input = f"{h}.{p}".encode()
    if alg == "none":
        pass                                    # nothing to check
    elif alg == "HS256":                        # the key is used as an HMAC secret
        if not hmac.compare_digest(b64d(s), hmac.new(key, signing_input, hashlib.sha256).digest()):
            raise ValueError("bad signature")
    elif alg == "RS256":
        public_key = serialization.load_pem_public_key(key)
        try:
            public_key.verify(b64d(s), signing_input, padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature:
            raise ValueError("bad signature")
    return json.loads(b64d(p))


def pinned_verify(token: str, key: bytes) -> dict:
    return jwt.decode(token, key, algorithms=["RS256"])


now = int(time.time())
real = jwt.encode({"sub": "alice", "role": "customer", "exp": now + 300}, rsa_key, algorithm="RS256")
admin = b64e(json.dumps({"sub": "mallory", "role": "admin", "exp": now + 300}).encode())

# Forgery 1: alg=none and an empty signature.
none_token = f"{b64e(b'{\"alg\":\"none\"}')}.{admin}."
# Forgery 2: alg=HS256, "signed" with the PUBLIC key as the HMAC secret.
# Anyone can do this, because the public key is public (for example in the JWKS).
hs_header = b64e(b'{"alg":"HS256","typ":"JWT"}')
mac = hmac.new(PUBLIC_PEM, f"{hs_header}.{admin}".encode(), hashlib.sha256).digest()
confused_token = f"{hs_header}.{admin}.{b64e(mac)}"

for name, token in [("real RS256 token", real), ("forged alg=none", none_token),
                    ("forged HS256 with public key", confused_token)]:
    print(f"== {name}")
    for verifier in (naive_verify, pinned_verify):
        try:
            print(f"   {verifier.__name__:14}: accepted {verifier(token, PUBLIC_PEM)}")
        except Exception as exc:
            print(f"   {verifier.__name__:14}: rejected, {type(exc).__name__} - {exc}")
