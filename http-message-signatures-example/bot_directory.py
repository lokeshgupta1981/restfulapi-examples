"""The bot operator's key directory: a JWK Set at the well-known URL.

It publishes only the PUBLIC part of the bot key and signs each response with
that key (tag "http-message-signatures-directory"), as the Web Bot Auth draft
recommends in Appendix B.1.

Run: uvicorn bot_directory:app --port 8001
"""
import json
import time

from fastapi import FastAPI, Request, Response

from httpsig import Message, content_digest, private_key_from_jwk, sign

with open("keys/demo-bot-key.json") as f:
    BOT_KEY = json.load(f)
PRIVATE_KEY = private_key_from_jwk(BOT_KEY)
PUBLIC_JWK = {k: BOT_KEY[k] for k in ("kty", "crv", "kid", "x")}  # never publish "d"

app = FastAPI()


@app.get("/.well-known/http-message-signatures-directory")
def directory(request: Request):
    body = json.dumps({"keys": [PUBLIC_JWK]}, separators=(",", ":")).encode()
    now = int(time.time())
    headers = {"content-digest": content_digest(body)}
    req = Message(method="GET", url=str(request.url))
    resp = Message(status=200, headers=headers, request=req)
    _, sig_input, signature = sign(
        resp, "binding",
        [("@authority", {"req": True}), "content-digest"],
        {"created": now, "expires": now + 300, "keyid": PUBLIC_JWK["kid"],
         "tag": "http-message-signatures-directory"},
        PRIVATE_KEY,
    )
    headers.update({"signature-input": sig_input, "signature": signature,
                    "cache-control": "max-age=300"})
    return Response(body, headers=headers,
                    media_type="application/http-message-signatures-directory+json")
