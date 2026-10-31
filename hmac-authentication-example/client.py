"""Signs requests for the Orders API and sends the ten test requests from the article.

Run: python client.py  (server on http://localhost:9410)
"""
import json
import secrets
import time
from urllib.parse import urlsplit

import httpx

from signing import canonical_request, sign

BASE = "http://localhost:9410"
KEY_ID = "client-1-2026-10"
SECRET = b"demo-secret-key-2026-10"  # example value, not a real key


def auth_header(key_id, ts, nonce, sig):
    return f'HMAC-SHA256 keyId="{key_id}", ts="{ts}", nonce="{nonce}", sig="{sig}"'


def send(label, path, method="POST", body=b"", signed_body=None, ts=None, nonce=None,
         key_id=KEY_ID, secret=SECRET):
    url = urlsplit(BASE + path)
    ts = str(ts or int(time.time()))
    nonce = nonce or secrets.token_hex(12)
    to_sign = body if signed_body is None else signed_body
    canonical = canonical_request(method, url.netloc, url.path, url.query, ts, nonce, to_sign)
    headers = {"Authorization": auth_header(key_id, ts, nonce, sign(secret, canonical))}
    if method == "POST":
        headers["Content-Type"] = "application/json"
    response = httpx.request(method, BASE + path, headers=headers,
                             content=body if method == "POST" else None)
    print("--- " + label)
    print(response.status_code, response.text)
    return headers, ts, nonce


order = json.dumps({"item": "keyboard", "quantity": 2}, separators=(",", ":")).encode()

headers, ts, nonce = send("1. valid signed POST", "/orders?note=gift+wrap&currency=USD", body=order)
print("Authorization:", headers["Authorization"])

send("2. replay of request 1 (same nonce and timestamp)",
     "/orders?note=gift+wrap&currency=USD", body=order, ts=ts, nonce=nonce)

send("3. body changed after signing", "/orders",
     body=b'{"item":"keyboard","quantity":20}', signed_body=order)

send("4. timestamp 10 minutes old", "/orders", body=order, ts=int(time.time()) - 600)

send("5. same query, %20 instead of + and other order",
     "/orders?currency=USD&note=gift%20wrap", body=order)

send("6. GET with an empty body", "/orders/1001", method="GET")

send("7. old key during rotation", "/orders", body=order,
     key_id="client-1-2026-07", secret=b"demo-secret-key-2026-07")

send("8. retired key", "/orders", body=order,
     key_id="client-1-2026-04", secret=b"demo-secret-key-2026-04")

send("9. wrong secret for a known keyId", "/orders", body=order, secret=b"demo-secret-key-typo")

send("10. server verifies a re-serialized body (bug)", "/buggy/orders", body=order)
