"""PKCE helpers (RFC 7636): create a code verifier and its S256 code challenge.

Run: python pkce.py
"""
import base64
import hashlib
import secrets


def b64url(data: bytes) -> str:
    # Base64URL without "=" padding (RFC 7636, Appendix A).
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_verifier() -> str:
    # 32 random bytes -> 43 characters from [A-Z a-z 0-9 - _].
    return b64url(secrets.token_bytes(32))


def make_challenge(verifier: str) -> str:
    # S256: BASE64URL(SHA256(ASCII(code_verifier)))
    return b64url(hashlib.sha256(verifier.encode("ascii")).digest())


if __name__ == "__main__":
    # Test vector from RFC 7636, Appendix B.
    rfc_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    rfc_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    print("RFC 7636 Appendix B")
    print("  verifier :", rfc_verifier)
    print("  challenge:", make_challenge(rfc_verifier))
    print("  matches  :", make_challenge(rfc_verifier) == rfc_challenge)

    verifier = make_verifier()
    print("A fresh pair")
    print("  verifier :", verifier, f"({len(verifier)} chars)")
    print("  challenge:", make_challenge(verifier), f"({len(make_challenge(verifier))} chars)")
