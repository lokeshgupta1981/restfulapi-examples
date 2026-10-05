"""Base64 vs Base64URL in Python (standard library only).

Run: python3 encoding_demo.py
"""

import base64
import binascii
import hashlib
import hmac
import json
import math

# 1. The same bytes in both alphabets
data = b"<<???>>"
standard = base64.b64encode(data).decode("ascii")
url_safe = base64.urlsafe_b64encode(data).decode("ascii")
url_safe_no_pad = url_safe.rstrip("=")
print("1. Same 7 bytes, two alphabets")
print("   input           :", data)
print("   base64          :", standard)
print("   base64url       :", url_safe)
print("   base64url no pad:", url_safe_no_pad)

# 2. Padding: 1, 2 or 3 bytes in the last group
print("\n2. Padding by input length")
for text in [b"a", b"ab", b"abc", b"abcd"]:
    print(f"   {len(text)} byte(s) {text!r:8} -> {base64.b64encode(text).decode()}")

# 3. Size overhead
print("\n3. Encoded size")
for size in [3, 100, 1024, 1_000_000]:
    padded = 4 * math.ceil(size / 3)
    unpadded = math.ceil(size * 4 / 3)
    print(f"   {size:>9} bytes -> base64 {padded:>9} chars, "
          f"base64url no pad {unpadded:>9} chars (+{(padded - size) / size:.1%})")

# 4. Decoding Base64URL without padding: the stdlib needs the '=' back
print("\n4. urlsafe_b64decode() and missing padding")
try:
    base64.urlsafe_b64decode(url_safe_no_pad)
except binascii.Error as error:
    print("   urlsafe_b64decode('PDw_Pz8-Pg') ->", type(error).__name__, error)


def b64url_decode(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded)


print("   b64url_decode('PDw_Pz8-Pg')     ->", b64url_decode(url_safe_no_pad))

# 5. The silent bug: standard b64decode() drops '-' and '_' by default
print("\n5. Decoding base64url text with the standard decoder")
tricky = bytes([0xFB, 0xFF, 0xBF, 0x01, 0x02, 0x03])
tricky_url = base64.urlsafe_b64encode(tricky).decode()
print("   original bytes        :", tricky.hex(" "))
print("   base64url text        :", tricky_url)
print("   b64decode(text)       :", base64.b64decode(tricky_url).hex(" "), "(no error!)")
try:
    base64.b64decode(tricky_url, validate=True)
except binascii.Error as error:
    print("   b64decode(validate=True) ->", type(error).__name__, error)

# 6. A JWT uses base64url without padding in all three parts
print("\n6. JWT segments")
key = b"demo-signing-key"
header = {"alg": "HS256", "typ": "JWT"}
claims = {"sub": "user-42", "scope": "orders:read", "exp": 1791000000}
segments = [
    base64.urlsafe_b64encode(json.dumps(part, separators=(",", ":")).encode()).rstrip(b"=")
    for part in (header, claims)
]
signing_input = b".".join(segments)
signature = hmac.new(key, signing_input, hashlib.sha256).digest()
token = (signing_input + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode()
print("   token:", token)
payload_part = token.split(".")[1]
signature_part = token.split(".")[2]
print(f"   payload segment length: {len(payload_part)} (length % 4 = {len(payload_part) % 4})")
try:
    base64.b64decode(payload_part)
except binascii.Error as error:
    print("   b64decode(payload)    ->", type(error).__name__, error)
print("   b64url_decode(payload)->", b64url_decode(payload_part).decode())
print("   signature bytes             :", len(b64url_decode(signature_part)))
