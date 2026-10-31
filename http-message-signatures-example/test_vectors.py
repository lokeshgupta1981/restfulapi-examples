"""Checks httpsig.py against the published test vectors.

1. RFC 9421 Appendix B.2.6 (Ed25519 request signature)
2. draft-ietf-webbotauth-httpsig-protocol-01 Appendix E.2.1 (Web Bot Auth, Ed25519)

Ed25519 signatures are deterministic, so the same key and signature base must
give exactly the signature printed in the documents.
"""
import json

from httpsig import Message, jwk_thumbprint, private_key_from_jwk, sign

# Published TEST key from RFC 9421 Appendix B.1.4. Never use it for anything real.
with open("keys/rfc9421-test-key-ed25519.json") as f:
    TEST_KEY = json.load(f)
private_key = private_key_from_jwk(TEST_KEY)

# The RFC's test-request (Appendix B.2)
test_request = Message(
    method="POST",
    url="https://example.com/foo?param=Value&Pet=dog",
    headers={
        "host": "example.com",
        "date": "Tue, 20 Apr 2021 02:07:55 GMT",
        "content-type": "application/json",
        "content-length": "18",
    },
)

print("== RFC 9421 B.2.6: signing a request using ed25519")
base, sig_input, signature = sign(
    test_request, "sig-b26",
    ["date", "@method", "@path", "@authority", "content-type", "content-length"],
    {"created": 1618884473, "keyid": "test-key-ed25519"},
    private_key,
)
print(base)
print("Signature-Input:", sig_input)
print("Signature:", signature)
expected = ("sig-b26=:wqcAqbmYJ2ji2glfAMaRy4gruYYnx2nEFN2HN6jrnDnQCK1"
            "u02Gb04v9EDgwUPiu4A0w6vuQv5lIp5WPpBKRCw==:")
print("matches the RFC:", signature == expected)

print()
print("== Web Bot Auth draft E.2.1: Signature-Agent present on the request")
print("JWK thumbprint of the test key:", jwk_thumbprint(TEST_KEY))
bot_request = Message(
    method="GET",
    url="https://example.com/",
    headers={"signature-agent": 'sig2="https://signature-agent.test"'},
)
base, sig_input, signature = sign(
    bot_request, "sig2",
    ["@authority", ("signature-agent", {"key": "sig2"})],
    {
        "created": 1735689600,
        "keyid": jwk_thumbprint(TEST_KEY),
        "alg": "ed25519",
        "expires": 4889289600,
        "nonce": "n9p433xm+NJ3ph3upfBIGmsuwHw387YV7Q/F+6BSpGCVjYCqQw6rznNA8PVVLySrAWsv0hQtFioQb6E1YsauiA==",
        "tag": "web-bot-auth",
    },
    private_key,
)
print(base)
print("Signature:", signature)
expected = "sig2=:CGokAoY/FrPpyuzTe1Fb2kLTAH9Idw6qSFd1+D77r1firsMRCxeuLu5e6O+ek3zQgDMAzjiXtLVfqE00xnABCQ==:"
print("matches the draft:", signature == expected)
