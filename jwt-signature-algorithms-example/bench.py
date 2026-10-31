"""Compares HS256, RS256, PS256, ES256 and EdDSA (Ed25519): signature size, token size,
whether signing the same claims twice gives the same signature, and sign/verify time.

Times are per operation, through PyJWT's jwt.encode() and jwt.decode(), median of 5 rounds.
"""
import base64
import os
import platform
import secrets
import statistics
import time

import cryptography
import jwt
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa

ROUNDS = 5
OPS = int(os.environ.get("BENCH_OPS", "2000"))
claims = {"iss": "http://127.0.0.1:8000", "sub": "alice", "aud": "orders-api",
          "scope": "orders:read", "iat": 1793350800, "exp": 1793351100}

rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ec_key = ec.generate_private_key(ec.SECP256R1())
ed_key = ed25519.Ed25519PrivateKey.generate()
setups = [  # alg, key description, signing key, verification key
    ("HS256", "256-bit shared secret", secrets.token_bytes(32), None),
    ("RS256", "RSA 2048", rsa_key, rsa_key.public_key()),
    ("PS256", "RSA 2048", rsa_key, rsa_key.public_key()),
    ("ES256", "P-256", ec_key, ec_key.public_key()),
    ("EdDSA", "Ed25519", ed_key, ed_key.public_key()),
]


def per_op_us(fn):
    rounds = []
    for _ in range(ROUNDS):
        start = time.perf_counter()
        for _ in range(OPS):
            fn()
        rounds.append((time.perf_counter() - start) / OPS * 1e6)
    return statistics.median(rounds)


print(f"Python {platform.python_version()}, PyJWT {jwt.__version__}, cryptography {cryptography.__version__}, "
      f"{platform.machine()}, {os.cpu_count()} CPUs, {OPS} ops x {ROUNDS} rounds")
print(f"{'alg':6} {'key':22} {'sig bytes':>9} {'token chars':>11} {'same sig twice':>14} "
      f"{'sign us':>8} {'verify us':>9}")
for alg, desc, sk, vk in setups:
    vk = vk or sk
    token = jwt.encode(claims, sk, algorithm=alg)
    again = jwt.encode(claims, sk, algorithm=alg)
    sig = token.split(".")[2]
    sig_bytes = len(base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)))
    opts = {"verify_exp": False, "verify_aud": False}
    sign = per_op_us(lambda: jwt.encode(claims, sk, algorithm=alg))
    verify = per_op_us(lambda: jwt.decode(token, vk, algorithms=[alg], options=opts))
    print(f"{alg:6} {desc:22} {sig_bytes:>9} {len(token):>11} {str(token == again):>14} "
          f"{sign:>8.1f} {verify:>9.1f}")
