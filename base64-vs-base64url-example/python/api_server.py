"""Small Orders API that uses Base64 and Base64URL the way real APIs do.

- POST /attachments      file content in JSON as standard Base64 (RFC 4648, section 4)
- GET  /orders           pagination cursor as Base64URL without padding (section 5)
- GET  /legacy/orders    the same cursor, encoded with standard Base64 (the bug)
- GET  /reports          HTTP Basic authentication (RFC 7617, standard Base64)

Run: python3 api_server.py            (listens on 127.0.0.1:9170, or $PORT)
Python standard library only.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PORT = int(os.environ.get("PORT", "9170"))
CURSOR_KEY = b"cursor-demo-key"  # demo only: load a real secret from config
BASIC_USER = "reports-app"
BASIC_PASSWORD = "s3cret-42"     # demo only

ORDERS = [
    {"id": f"ord_{n}", "total": f"{20 + n % 7}.50", "currency": "EUR"}
    for n in range(1000, 1006)
]

BASE64URL_CHARS = re.compile(r"^[A-Za-z0-9_-]*$")


# ---------- Base64URL helpers (no padding, strict alphabet) ----------

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    if not BASE64URL_CHARS.match(text) or len(text) % 4 == 1:
        raise ValueError("not a base64url string")
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded)


# ---------- signed pagination cursor ----------

def make_cursor_bytes(after_id: str) -> bytes:
    payload = json.dumps({"after": after_id}, separators=(",", ":")).encode()
    tag = hmac.new(CURSOR_KEY, payload, hashlib.sha256).digest()[:8]
    return payload + b"." + tag


def read_cursor_bytes(raw: bytes) -> str:
    payload, _, tag = raw.rpartition(b".")
    expected = hmac.new(CURSOR_KEY, payload, hashlib.sha256).digest()[:8]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("cursor signature does not match")
    return json.loads(payload)["after"]


def page_after(after_id):
    start = 0
    if after_id is not None:
        ids = [order["id"] for order in ORDERS]
        start = ids.index(after_id) + 1
    return ORDERS[start:start + 2]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def version_string(self):
        return "OrdersAPI/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------- response helpers ----------

    def send_json(self, status, body, headers=None):
        data = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_problem(self, status, title, detail, headers=None):
        body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
        data = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/problem+json")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- routes ----------

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        if url.path == "/orders":
            self.list_orders(query, legacy=False)
        elif url.path == "/legacy/orders":
            self.list_orders(query, legacy=True)
        elif url.path == "/reports":
            self.reports()
        else:
            self.send_problem(404, "Not Found", f"No route for {url.path}")

    def do_POST(self):
        if urlsplit(self.path).path == "/attachments":
            self.create_attachment()
        else:
            self.send_problem(404, "Not Found", "No route")

    def list_orders(self, query, legacy):
        after_id = None
        if "cursor" in query:
            cursor = query["cursor"][0]
            try:
                if legacy:
                    raw = base64.b64decode(cursor, validate=True)
                else:
                    raw = b64url_decode(cursor)
                after_id = read_cursor_bytes(raw)
            except (ValueError, binascii.Error, KeyError) as error:
                self.send_problem(400, "Bad Request",
                                  f"Invalid cursor {cursor!r}: {error}")
                return
        items = page_after(after_id)
        body = {"items": items}
        if items and items[-1]["id"] != ORDERS[-1]["id"]:
            raw = make_cursor_bytes(items[-1]["id"])
            if legacy:
                body["next_cursor"] = base64.b64encode(raw).decode("ascii")
            else:
                body["next_cursor"] = b64url_encode(raw)
        self.send_json(200, body)

    def create_attachment(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            doc = json.loads(self.rfile.read(length))
            content = base64.b64decode(doc["content_base64"], validate=True)
        except (ValueError, KeyError, binascii.Error) as error:
            self.send_problem(400, "Bad Request",
                              f"content_base64 must be standard Base64 "
                              f"(RFC 4648, section 4): {error}")
            return
        digest = hashlib.sha256(content).digest()
        body = {
            "id": "att_" + b64url_encode(digest[:6]),
            "file_name": doc.get("file_name"),
            "size_bytes": len(content),
        }
        headers = {"Content-Digest": "sha-256=:" + base64.b64encode(digest).decode() + ":"}
        self.send_json(201, body, headers)

    def reports(self):
        challenge = {"WWW-Authenticate": 'Basic realm="reports", charset="UTF-8"'}
        header = self.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "basic" or not token:
            self.send_problem(401, "Unauthorized", "Basic credentials required", challenge)
            return
        try:
            user_pass = base64.b64decode(token, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            self.send_problem(400, "Bad Request", "Credentials are not valid Base64")
            return
        user, _, password = user_pass.partition(":")
        if user != BASIC_USER or not hmac.compare_digest(password, BASIC_PASSWORD):
            self.send_problem(401, "Unauthorized",
                              "Wrong user or password",
                              challenge)
            return
        self.send_json(200, {"report": "daily-sales", "orders": len(ORDERS)})


if __name__ == "__main__":
    print(f"Orders API on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
