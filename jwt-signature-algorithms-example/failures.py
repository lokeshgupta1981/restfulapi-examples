"""Reproduces the most common JWT signature verification errors with PyJWT."""
import base64
import time
import warnings

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

warnings.simplefilter("always")  # show PyJWT's warnings in the output

SECRET = bytes.fromhex("6b7f3c0e9a1d4e2f8b5a7c3d1e9f0a2b4c6d8e0f1a3b5c7d9e1f3a5b7c9d1e3f")  # demo key
rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
other_rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ec_key = ec.generate_private_key(ec.SECP256R1())
now = int(time.time())
claims = {"sub": "alice", "iat": now, "exp": now + 300}


def attempt(title, token, key, **kwargs):
    print(f"== {title}")
    try:
        with warnings.catch_warnings(record=True) as caught:
            jwt.decode(token, key, **kwargs)
        for w in caught:
            print("   warning:", w.category.__name__, "-", w.message)
        print("   OK, signature valid")
    except Exception as exc:
        print("  ", type(exc).__name__, "-", exc)


hs = jwt.encode(claims, SECRET, algorithm="HS256")
rs = jwt.encode(claims, rsa_key, algorithm="RS256")
es = jwt.encode(claims, ec_key, algorithm="ES256")

attempt("1. Correct key, pinned algorithm", rs, rsa_key.public_key(), algorithms=["RS256"])
attempt("2. No algorithms argument", rs, rsa_key.public_key())
attempt("3. Wrong secret", hs, b"another-32-byte-demo-secret-0000", algorithms=["HS256"])
attempt("4. Secret stored as base64 text, used without decoding", hs,
        base64.b64encode(SECRET), algorithms=["HS256"])
attempt("5. Public key of a different key pair", rs, other_rsa_key.public_key(), algorithms=["RS256"])
attempt("6. Token is RS256, verifier only allows HS256", rs, SECRET, algorithms=["HS256"])
attempt("7. Key type does not match the algorithm (RSA key, ES256 token)", es, rsa_key.public_key(), algorithms=["ES256"])
attempt("8. Token cut short by one character during copy and paste", rs[:-1],
        rsa_key.public_key(), algorithms=["RS256"])
expired = jwt.encode(dict(claims, exp=now - 60), rsa_key, algorithm="RS256")
attempt("9. Valid signature, but the token expired", expired, rsa_key.public_key(), algorithms=["RS256"])
with warnings.catch_warnings(record=True) as caught:
    short = jwt.encode(claims, b"secret", algorithm="HS256")
print("== 10a. Signing HS256 with a 6-byte secret")
print("   warning:", caught[0].category.__name__, "-", caught[0].message)
attempt("10b. Verifying that token", short, b"secret", algorithms=["HS256"])
pem = rsa_key.public_key().public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo)
attempt("11. RSA public key PEM used as an HS256 secret", hs, pem, algorithms=["HS256"])
