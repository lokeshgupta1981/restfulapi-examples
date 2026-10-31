"""DPoP helpers (RFC 9449): create proofs on the client, check them on the server.

Demo code for learning. It covers the checks of RFC 9449, section 4.3, for ES256 keys.
"""
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlsplit, urlunsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

ALGS = ["ES256"]          # signature algorithms we accept in DPoP proofs
PROOF_MAX_AGE = 60        # seconds a proof stays valid after its iat
CLOCK_SKEW = 5            # seconds a proof may come "from the future"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


# ---------- client side ----------

def new_key():
    """A fresh P-256 key pair. The private key never leaves the client."""
    return ec.generate_private_key(ec.SECP256R1())


def public_jwk(key) -> dict:
    nums = key.public_key().public_numbers()
    return {"kty": "EC", "crv": "P-256",
            "x": b64url(nums.x.to_bytes(32, "big")),
            "y": b64url(nums.y.to_bytes(32, "big"))}


def jwk_thumbprint(jwk: dict) -> str:
    """RFC 7638 SHA-256 thumbprint: required members only, sorted, no spaces."""
    required = {"EC": ["crv", "kty", "x", "y"], "RSA": ["e", "kty", "n"],
                "OKP": ["crv", "kty", "x"]}[jwk["kty"]]
    canonical = json.dumps({k: jwk[k] for k in required}, separators=(",", ":"), sort_keys=True)
    return b64url(hashlib.sha256(canonical.encode()).digest())


def access_token_hash(access_token: str) -> str:
    """The ath claim: base64url(SHA-256(ASCII bytes of the access token))."""
    return b64url(hashlib.sha256(access_token.encode("ascii")).digest())


def htu_of(url: str) -> str:
    """The htu value: the request URL without query and fragment."""
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def make_proof(key, method: str, url: str, access_token: str | None = None,
               nonce: str | None = None, iat: int | None = None) -> str:
    claims = {"jti": secrets.token_urlsafe(16), "htm": method, "htu": htu_of(url),
              "iat": int(time.time()) if iat is None else iat}
    if access_token:
        claims["ath"] = access_token_hash(access_token)
    if nonce:
        claims["nonce"] = nonce
    headers = {"typ": "dpop+jwt", "jwk": public_jwk(key)}
    return jwt.encode(claims, key, algorithm="ES256", headers=headers)


# ---------- server side ----------

class DPoPError(Exception):
    def __init__(self, error: str, description: str):
        super().__init__(description)
        self.error, self.description = error, description


class ReplayCache:
    """Remembers jti values until their proofs expire. One process only (demo)."""

    def __init__(self):
        self.seen: dict[str, float] = {}
        self.last_cleanup = 0.0

    def check_and_store(self, jti: str, iat: int):
        now = time.time()
        if now - self.last_cleanup > 1:          # drop expired entries once per second
            self.seen = {k: v for k, v in self.seen.items() if v > now}
            self.last_cleanup = now
        if jti in self.seen:
            raise DPoPError("invalid_dpop_proof", "proof was already used (jti replay)")
        self.seen[jti] = iat + PROOF_MAX_AGE + CLOCK_SKEW


def verify_proof(proof_headers: list[str], method: str, url: str, replay: ReplayCache,
                 access_token: str | None = None, expected_nonce: str | None = None) -> str:
    """Runs the RFC 9449 section 4.3 checks. Returns the JWK thumbprint of the proof key."""
    if len(proof_headers) != 1:                                   # check 1
        raise DPoPError("invalid_dpop_proof", "expected exactly one DPoP header")
    proof = proof_headers[0]
    try:
        header = jwt.get_unverified_header(proof)                 # check 2
    except jwt.PyJWTError:
        raise DPoPError("invalid_dpop_proof", "DPoP header is not a JWT")
    if header.get("typ") != "dpop+jwt":                           # check 4
        raise DPoPError("invalid_dpop_proof", "typ must be dpop+jwt")
    if header.get("alg") not in ALGS:                             # check 5
        raise DPoPError("invalid_dpop_proof", f"alg must be one of {ALGS}")
    jwk = header.get("jwk")
    if not isinstance(jwk, dict) or "d" in jwk:                   # check 7
        raise DPoPError("invalid_dpop_proof", "jwk must be a public key")
    try:                                                          # check 6
        key = jwt.PyJWK(jwk, algorithm="ES256").key
        claims = jwt.decode(proof, key, algorithms=ALGS,
                            options={"require": ["jti", "htm", "htu", "iat"],
                                     "verify_iat": False})       # we check iat ourselves
    except jwt.PyJWTError as e:
        raise DPoPError("invalid_dpop_proof", f"bad proof: {e}")
    if claims["htm"] != method:                                   # check 8
        raise DPoPError("invalid_dpop_proof", f"htm {claims['htm']} does not match {method}")
    if htu_of(claims["htu"]) != htu_of(url):                      # check 9
        raise DPoPError("invalid_dpop_proof", f"htu {claims['htu']} does not match {htu_of(url)}")
    if expected_nonce is not None and claims.get("nonce") != expected_nonce:   # check 10
        raise DPoPError("use_dpop_nonce", "a fresh DPoP nonce is required")
    now = time.time()                                             # check 11
    if not (now - PROOF_MAX_AGE <= claims["iat"] <= now + CLOCK_SKEW):
        raise DPoPError("invalid_dpop_proof", "proof iat is outside the accepted window")
    if access_token is not None:                                  # check 12
        if claims.get("ath") != access_token_hash(access_token):
            raise DPoPError("invalid_dpop_proof", "ath does not match the access token")
    replay.check_and_store(claims["jti"], claims["iat"])         # replay protection (11.1)
    return jwk_thumbprint(jwk)
