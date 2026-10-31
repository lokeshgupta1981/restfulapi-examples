"""Verify a JWT against a JWKS step by step, without a JWT library.

Usage: python verify_by_hand.py <issuer> <token>
Shows what libraries such as PyJWKClient do for us.
"""
import base64
import json
import sys
import time

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

ALLOWED_ALGS = {"RS256", "ES256"}


def b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def b64url_int(part: str) -> int:
    return int.from_bytes(b64url_decode(part), "big")


def public_key_from_jwk(jwk: dict):
    if jwk["kty"] == "RSA":
        return rsa.RSAPublicNumbers(b64url_int(jwk["e"]), b64url_int(jwk["n"])).public_key()
    if jwk["kty"] == "EC" and jwk["crv"] == "P-256":
        return ec.EllipticCurvePublicNumbers(
            b64url_int(jwk["x"]), b64url_int(jwk["y"]), ec.SECP256R1()).public_key()
    raise ValueError(f"unsupported key type {jwk['kty']}")


def verify_signature(alg: str, key, signing_input: bytes, signature: bytes):
    if alg == "RS256":
        key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    elif alg == "ES256":  # JWS stores r || s, cryptography expects DER
        r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
        key.verify(encode_dss_signature(r, s), signing_input, ec.ECDSA(hashes.SHA256()))


def main(issuer: str, token: str):
    header_b64, payload_b64, signature_b64 = token.split(".")
    header = json.loads(b64url_decode(header_b64))
    print("1. Token header:", header)

    jwks_uri = httpx.get(f"{issuer}/.well-known/oauth-authorization-server").json()["jwks_uri"]
    jwks = httpx.get(jwks_uri).json()
    print("2. JWKS from", jwks_uri, "has kids", [k["kid"] for k in jwks["keys"]])

    jwk = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
    if jwk is None:
        sys.exit(f"   No key with kid {header.get('kid')!r}: reject the token")
    print(f"3. Picked key kid={jwk['kid']} kty={jwk['kty']} alg={jwk['alg']}")

    if header["alg"] not in ALLOWED_ALGS or header["alg"] != jwk["alg"]:
        sys.exit(f"   alg {header['alg']!r} not allowed for this key: reject the token")

    key = public_key_from_jwk(jwk)
    try:
        verify_signature(header["alg"], key, f"{header_b64}.{payload_b64}".encode(),
                         b64url_decode(signature_b64))
    except InvalidSignature:
        sys.exit("4. Signature INVALID: reject the token")
    print("4. Signature valid")

    claims = json.loads(b64url_decode(payload_b64))
    ok = claims["iss"] == issuer and claims["aud"] == "orders-api" and claims["exp"] > time.time()
    print("5. Claims:", {k: claims[k] for k in ("iss", "aud", "sub", "scope", "exp")},
          "-> accepted" if ok else "-> rejected")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
