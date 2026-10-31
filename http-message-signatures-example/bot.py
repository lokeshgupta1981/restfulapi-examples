"""bookstore-bot: an automated client that signs its requests with Web Bot Auth.

Runs ten scenarios against the Bookstore API (server.py). Start server.py and
bot_directory.py first, or use run_all.sh.

Environment: ORIGIN (default http://127.0.0.1:8000),
             AGENT_URL (default http://127.0.0.1:8001/.well-known/http-message-signatures-directory)
"""
import json
import os
import secrets
import time
from urllib.parse import urlsplit

import httpx

from httpsig import (Message, content_digest, jwk_thumbprint, private_key_from_jwk, sign)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ORIGIN = os.environ.get("ORIGIN", "http://127.0.0.1:8000")
AGENT_URL = os.environ.get(
    "AGENT_URL", "http://127.0.0.1:8001/.well-known/http-message-signatures-directory")

with open("keys/demo-bot-key.json") as f:
    BOT_KEY = json.load(f)
PRIVATE_KEY = private_key_from_jwk(BOT_KEY)
KEYID = jwk_thumbprint(BOT_KEY)


LAST_BASE = ""


def signed_headers(method, url, components, body=b"", lifetime=60, created=None,
                   key=PRIVATE_KEY, keyid=KEYID, legacy=False):
    """Signs one request and returns the headers to send."""
    created = int(time.time()) if created is None else created
    # legacy=True sends the older plain-string Signature-Agent form
    headers = {"signature-agent": f'"{AGENT_URL}"' if legacy else f'sig1="{AGENT_URL}"'}
    if body:
        headers["content-type"] = "application/json"
        headers["content-digest"] = content_digest(body)
    msg = Message(method=method, url=url, headers=headers)
    base, sig_input, signature = sign(
        msg, "sig1", components + ["signature-agent" if legacy else ("signature-agent", {"key": "sig1"})],
        {"created": created, "expires": created + lifetime, "keyid": keyid,
         "nonce": secrets.token_urlsafe(16), "tag": "web-bot-auth"},
        key,
    )
    global LAST_BASE
    LAST_BASE = base
    headers.update({"signature-input": sig_input, "signature": signature})
    return headers


def send(title, method, url, headers=None, body=b"", show_request=False):
    print(f"--- {title}")
    if show_request:
        print("signature base:")
        print(LAST_BASE)
        print()
        parts = urlsplit(url)
        print(f"{method} {parts.path} HTTP/1.1\nHost: {parts.netloc}")
        for k, v in (headers or {}).items():
            print(f"{'-'.join(w.capitalize() for w in k.split('-'))}: {v}")
        print()
    r = httpx.request(method, url, headers=headers, content=body, timeout=10)
    extra = f"\nAccept-Signature: {r.headers['accept-signature']}" if "accept-signature" in r.headers else ""
    print(f"{r.status_code} {r.text}{extra}")
    return r


book1 = f"{ORIGIN}/books/1"
send("1. unsigned request", "GET", book1)

h = signed_headers("GET", book1, ["@authority"])
send("2. signed GET, covering only @authority (the draft's minimum)", "GET", book1, h, show_request=True)

send("3. same headers replayed on another path", "GET", f"{ORIGIN}/books/2", h)

order = json.dumps({"bookId": 1, "quantity": 2}).encode()
send("4. same headers replayed on POST /orders", "POST", f"{ORIGIN}/orders", h, order)

orders = f"{ORIGIN}/orders"
ph = signed_headers("POST", orders, ["@method", "@authority", "@path", "content-digest"], order)
send("5. signed POST covering @method, @path and content-digest", "POST", orders, ph, order,
     show_request=True)

tampered = json.dumps({"bookId": 1, "quantity": 20}).encode()
send("6. body changed after signing", "POST", orders, ph, tampered)

host_changed = orders.replace("127.0.0.1", "localhost")
send("7. same request arrives with a different Host (a proxy rewrote it)", "POST", host_changed, ph, order)

old = int(time.time()) - 600
send("8. expired signature", "GET", book1, signed_headers("GET", book1, ["@authority"], created=old))

send("9. signature valid for 24 hours", "GET", book1,
     signed_headers("GET", book1, ["@authority"], lifetime=86400))

other = Ed25519PrivateKey.generate()   # a key the directory does not publish
send("10. signed with a key that is not in the directory", "GET", book1,
     signed_headers("GET", book1, ["@authority"], key=other, keyid="unknown-key-id"))

send("11. older plain-string Signature-Agent form", "GET", book1,
     signed_headers("GET", book1, ["@authority"], legacy=True), show_request=True)
