"""Orders API that uses Base64 and Base64URL the way real APIs do.

- GET  /orders           pagination cursor in Base64URL without padding (RFC 4648, section 5)
- GET  /legacy/orders    the same cursor in standard Base64 (section 4): breaks in a URL
- POST /attachments      file content in JSON as standard Base64
- GET  /reports          HTTP Basic authentication (RFC 7617, standard Base64)

Run: uvicorn server:app --host 127.0.0.1 --port 9170
"""

import base64
import binascii
import hashlib
import hmac
import json
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

CURSOR_KEY = b"cursor-demo-key"  # demo value only: load a real secret from config
BASIC_USER = "reports-app"
BASIC_PASSWORD = "s3cret-42"     # demo value only

ORDERS = [
    {"id": f"ord_{n}", "total": f"{20 + n % 7}.50", "currency": "EUR"}
    for n in range(1000, 1006)
]

app = FastAPI()


class PrettyJSON(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, indent=2).encode()


def problem(status: int, title: str, detail: str, headers=None) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return PrettyJSON(body, status_code=status, headers=headers,
                      media_type="application/problem+json")


# ---------- Base64URL helpers: no padding, strict alphabet ----------

BASE64URL_CHARS = re.compile(r"^[A-Za-z0-9_-]*$")


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    if not BASE64URL_CHARS.match(text) or len(text) % 4 == 1:
        raise ValueError("not a base64url string")
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded)


# ---------- signed pagination cursor ----------

def make_cursor(after_id: str) -> bytes:
    payload = json.dumps({"after": after_id}, separators=(",", ":")).encode()
    tag = hmac.new(CURSOR_KEY, payload, hashlib.sha256).digest()[:8]
    return payload + b"." + tag


def read_cursor(raw: bytes) -> str:
    payload, _, tag = raw.rpartition(b".")
    expected = hmac.new(CURSOR_KEY, payload, hashlib.sha256).digest()[:8]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("cursor signature does not match")
    return json.loads(payload)["after"]


def page(after_id, encode):
    start = 0
    if after_id is not None:
        start = [o["id"] for o in ORDERS].index(after_id) + 1
    items = ORDERS[start:start + 2]
    body = {"items": items}
    if items and items[-1]["id"] != ORDERS[-1]["id"]:
        body["next_cursor"] = encode(make_cursor(items[-1]["id"]))
    return PrettyJSON(body)


# ---------- routes ----------

@app.get("/orders")
def list_orders(cursor: str | None = None):
    after_id = None
    if cursor is not None:
        try:
            after_id = read_cursor(b64url_decode(cursor))
        except (ValueError, binascii.Error, KeyError) as error:
            return problem(400, "Bad Request", f"Invalid cursor {cursor!r}: {error}")
    return page(after_id, b64url_encode)


@app.get("/legacy/orders")
def list_orders_legacy(cursor: str | None = None):
    after_id = None
    if cursor is not None:
        try:
            after_id = read_cursor(base64.b64decode(cursor, validate=True))
        except (ValueError, binascii.Error, KeyError) as error:
            return problem(400, "Bad Request", f"Invalid cursor {cursor!r}: {error}")
    return page(after_id, lambda raw: base64.b64encode(raw).decode("ascii"))


class Attachment(BaseModel):
    file_name: str
    content_base64: str


@app.post("/attachments", status_code=201)
def create_attachment(attachment: Attachment):
    try:
        content = base64.b64decode(attachment.content_base64, validate=True)
    except binascii.Error as error:
        return problem(400, "Bad Request",
                       f"content_base64 must be standard Base64: {error}")
    digest = hashlib.sha256(content).digest()
    body = {
        "id": "att_" + b64url_encode(digest[:6]),
        "file_name": attachment.file_name,
        "size_bytes": len(content),
    }
    headers = {"Content-Digest": "sha-256=:" + base64.b64encode(digest).decode() + ":"}
    return PrettyJSON(body, status_code=201, headers=headers)


@app.get("/reports")
def reports(request: Request):
    challenge = {"WWW-Authenticate": 'Basic realm="reports", charset="UTF-8"'}
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "basic" or not token:
        return problem(401, "Unauthorized", "Basic credentials required", challenge)
    try:
        user_pass = base64.b64decode(token, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return problem(400, "Bad Request", "Credentials are not valid Base64")
    user, _, password = user_pass.partition(":")
    if user != BASIC_USER or not hmac.compare_digest(password, BASIC_PASSWORD):
        return problem(401, "Unauthorized", "Wrong user or password", challenge)
    return PrettyJSON({"report": "daily-sales", "orders": len(ORDERS)})
