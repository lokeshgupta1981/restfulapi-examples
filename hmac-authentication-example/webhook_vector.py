"""Checks the published GitHub webhook test vector with Python's hmac module."""
import hashlib
import hmac
import json

secret = b"It's a Secret to Everybody"  # test value from the GitHub docs
payload = b"Hello, World!"
expected = "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"

computed = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
print(computed)
print("matches:", hmac.compare_digest(computed, expected))

# The same check fails when a framework hands us re-serialized JSON
raw = b'{"item":"keyboard","quantity":2}'
reserialized = json.dumps(json.loads(raw)).encode()
print(raw.decode())
print(reserialized.decode())
print("same bytes:", raw == reserialized)
