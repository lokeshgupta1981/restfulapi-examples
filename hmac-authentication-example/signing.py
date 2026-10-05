"""Canonical request and HMAC-SHA256 signature for the Orders API (scheme "HMAC-SHA256")."""
import hashlib
import hmac
from urllib.parse import parse_qsl, quote


def canonical_query(raw_query: str) -> str:
    # Decode every pair, sort by name and value, encode again with %20 for spaces.
    pairs = parse_qsl(raw_query, keep_blank_values=True)
    pairs.sort()
    encoded = [quote(name, safe="-_.~") + "=" + quote(value, safe="-_.~") for name, value in pairs]
    return "&".join(encoded)


def canonical_request(method: str, host: str, path: str, raw_query: str,
                      timestamp: str, nonce: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    lines = [
        method.upper(),
        host.lower(),
        path,
        canonical_query(raw_query),
        timestamp,
        nonce,
        body_hash,
    ]
    return "\n".join(lines)


def sign(secret: bytes, canonical: str) -> str:
    mac = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def signatures_match(expected_hex: str, received_hex: str) -> bool:
    # compare_digest takes the same time whether the first or the last byte differs
    return hmac.compare_digest(expected_hex.encode("ascii"), received_hex.encode("ascii"))


if __name__ == "__main__":
    demo_secret = b"demo-secret-key-2026-10"  # example value, not a real key
    body = b'{"item":"keyboard","quantity":2}'
    canonical = canonical_request("POST", "localhost:9410", "/orders",
                                  "note=gift+wrap&currency=USD",
                                  "1791200000", "n-0001", body)
    print(canonical)
    signature = sign(demo_secret, canonical)
    print("signature:", signature)
    print("same value:", signatures_match(signature, signature))
    print("uppercase hex:", signatures_match(signature, signature.upper()))
    print("first 10 characters:", signatures_match(signature, signature[:10]))
