"""HTTP Message Signatures (RFC 9421) with hmac-sha256.

1. Rebuilds the RFC 9421 test case B.2.5 and checks the published signature.
2. Signs an Orders API request with our own code.
3. Verifies that signature with the http-message-signatures library.
"""
import base64
import datetime
import hashlib
import hmac

import requests
from http_message_signatures import (HTTPMessageVerifier, HTTPSignatureKeyResolver,
                                     InvalidSignature, algorithms)


def signature_base(components, params):
    lines = ['"' + name + '": ' + value for name, value in components]
    lines.append('"@signature-params": ' + params)
    return "\n".join(lines)


def hmac_sha256_b64(secret: bytes, base: str) -> str:
    mac = hmac.new(secret, base.encode("ascii"), hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")


# --- 1. RFC 9421 appendix B.2.5 test case
test_shared_secret = base64.b64decode(
    "uzvJfB4u3N0Jy4T7NZ75MDVcr8zSTInedJtkgcu46YW4XByzNJjxBdtjUkdJPBt"
    "bmHhIDi6pcl8jsasjlTMtDQ==")
b25_params = '("date" "@authority" "content-type");created=1618884473;keyid="test-shared-secret"'
b25_base = signature_base([("date", "Tue, 20 Apr 2021 02:07:55 GMT"),
                           ("@authority", "example.com"),
                           ("content-type", "application/json")], b25_params)
print("B.2.5 signature:", hmac_sha256_b64(test_shared_secret, b25_base))
print("RFC 9421 value:  pxcQw6G3AjtMBQjwo8XzkZf/bws5LelbaMk5rGIGtE8=")

# --- 2. Sign an Orders API request
secret = b"demo-secret-key-2026-10"  # example value, not a real key
body = b'{"item":"keyboard","quantity":2}'
digest = base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
content_digest = "sha-256=:" + digest + ":"
created = 1791200000
params = ('("@method" "@authority" "@path" "@query" "content-digest" "content-type")'
          ';created=' + str(created) + ';nonce="n-0001";keyid="client-1-2026-10"')
base = signature_base([("@method", "POST"),
                       ("@authority", "localhost:9410"),
                       ("@path", "/orders"),
                       ("@query", "?currency=USD&note=gift%20wrap"),
                       ("content-digest", content_digest),
                       ("content-type", "application/json")], params)
signature = hmac_sha256_b64(secret, base)
print()
print(base)
print()
print("Content-Digest: " + content_digest)
print("Signature-Input: sig1=" + params)
print("Signature: sig1=:" + signature + ":")


# --- 3. Verify with an independent implementation
class DemoKeys(HTTPSignatureKeyResolver):
    def resolve_public_key(self, key_id):
        return {"client-1-2026-10": secret}[key_id]


def build_request(sent_body):
    prepared = requests.Request("POST", "http://localhost:9410/orders?currency=USD&note=gift%20wrap",
                                data=sent_body,
                                headers={"Content-Type": "application/json"}).prepare()
    prepared.headers["Content-Digest"] = content_digest
    prepared.headers["Signature-Input"] = "sig1=" + params
    prepared.headers["Signature"] = "sig1=:" + signature + ":"
    return prepared


verifier = HTTPMessageVerifier(signature_algorithm=algorithms.HMAC_SHA256,
                               key_resolver=DemoKeys())
age = datetime.timedelta(days=3650)
result = verifier.verify(build_request(body), max_age=age)
print()
print("library verify: valid,", result[0].label, result[0].parameters["keyid"])

# The library checks the signature, not the body: the receiver must compare
# Content-Digest with the bytes it got.
tampered = build_request(b'{"item":"keyboard","quantity":20}')
verifier.verify(tampered, max_age=age)
real_digest = "sha-256=:" + base64.b64encode(
    hashlib.sha256(tampered.body).digest()).decode("ascii") + ":"
print("tampered body, signature still valid; digest matches body:",
      real_digest == tampered.headers["Content-Digest"])

tampered.headers["Content-Type"] = "text/plain"
try:
    verifier.verify(tampered, max_age=age)
except InvalidSignature:
    print("changed Content-Type: signature rejected (InvalidSignature)")
