"""Bookstore API (the origin) that verifies Web Bot Auth signatures.

Verification steps:
 1. No signature headers           -> 403 with Accept-Signature (what to sign)
 2. Malformed headers               -> 400
 3. Find the signature with tag="web-bot-auth"
 4. Check covered components and created/expires against our policy
 5. Resolve the Signature-Agent URL to a key directory (cached, bounded fetch)
 6. Select the key by keyid, rebuild the signature base, verify
 7. For a body: compare Content-Digest with the SHA-256 of the raw body

Run: uvicorn server:app --port 8000
"""
import json
import time
from urllib.parse import urlsplit

import http_sfv
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from httpsig import (Message, SignatureError, content_digest, jwk_thumbprint,
                     parse_signatures, public_key_from_jwk, verify)

WELL_KNOWN = "/.well-known/http-message-signatures-directory"
MAX_LIFETIME = 300        # our policy: expires - created must be <= 5 minutes
CLOCK_SKEW = 30           # seconds we tolerate for "created" in the future
# Demo only: the spec requires https for directories. We allow plain http for localhost.
HTTP_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
# Known test keys MUST NOT be trusted (draft section 6.8). This is the RFC 9421 B.1.4 key.
TEST_KEY_THUMBPRINTS = {"poqkLGiymh_W0uP6PZFw-dvez3QJT5SolqXBCW38r0U"}

ACCEPT_SIGNATURE = ('sig1=("@method" "@authority" "@path" "signature-agent";key="sig1")'
                    ';created;expires;tag="web-bot-auth"')

# What each kind of request must cover, in addition to "signature-agent";key=<label>
REQUIRED = {
    "GET": {"@authority"},
    "POST": {"@authority", "@method", "@path", "content-digest"},
}

BOOKS = {1: {"id": 1, "title": "RESTful Web APIs"}, 2: {"id": 2, "title": "HTTP: The Definitive Guide"}}
directory_cache = {}      # url -> (expires_at, {keyid: jwk})

app = FastAPI()


class Rejected(Exception):
    def __init__(self, status, detail, headers=None):
        self.status, self.detail, self.headers = status, detail, headers or {}


@app.exception_handler(Rejected)
def rejected(_, exc: Rejected):
    return JSONResponse({"title": "Bot verification failed", "status": exc.status, "detail": exc.detail},
                        status_code=exc.status, headers=exc.headers,
                        media_type="application/problem+json")


def resolve_directory(url: str) -> dict:
    """Fetches the JWK Set for a Signature-Agent URL; returns {thumbprint: jwk}."""
    parts = urlsplit(url)
    if parts.path in ("", "/"):                 # bare origin, as older agents send
        url = f"{parts.scheme}://{parts.netloc}{WELL_KNOWN}"
    if parts.scheme != "https" and parts.hostname not in HTTP_ALLOWED_HOSTS:
        raise Rejected(403, "Signature-Agent must be an https URL")
    cached = directory_cache.get(url)
    if cached and cached[0] > time.time():
        return cached[1]
    try:   # bounded fetch: short timeout, no redirects, size limit (SSRF and DoS)
        r = httpx.get(url, timeout=2.0, follow_redirects=False,
                      headers={"Accept": "application/http-message-signatures-directory+json"})
    except httpx.HTTPError:
        raise Rejected(403, "unverified: key directory unreachable") from None
    if r.status_code != 200 or len(r.content) > 64_000:
        raise Rejected(403, f"unverified: key directory returned {r.status_code}")
    keys = {}
    for jwk in r.json().get("keys", [])[:10]:
        thumb = jwk_thumbprint(jwk)
        if thumb in TEST_KEY_THUMBPRINTS:
            continue
        keys[thumb] = jwk
    # The directory signs its own response: check it with the keys it publishes.
    resp = Message(status=200, headers=dict(r.headers), request=Message(method="GET", url=url))
    for label, (covered, sig) in parse_signatures(resp).items():
        jwk = keys.get(covered.params.get("keyid"))
        if jwk and covered.params.get("tag") == "http-message-signatures-directory":
            try:
                verify(resp, covered, sig, public_key_from_jwk(jwk))
            except SignatureError:
                raise Rejected(403, "key directory signature is invalid") from None
            if r.headers.get("content-digest") != content_digest(r.content):
                raise Rejected(403, "directory body does not match its Content-Digest")
    print(f"[origin] fetched key directory {url}: {len(keys)} key(s)", flush=True)
    directory_cache[url] = (time.time() + 300, keys)
    return keys


async def verify_bot(request: Request) -> dict:
    h = {k.lower(): v for k, v in request.headers.items()}
    if "signature" not in h and "signature-input" not in h:
        raise Rejected(403, "this endpoint is for signed bots only",
                       {"Accept-Signature": ACCEPT_SIGNATURE})
    msg = Message(method=request.method, url=f"http://{h['host']}{request.url.path}"
                  + (f"?{request.url.query}" if request.url.query else ""), headers=h)
    try:
        signatures = parse_signatures(msg)
    except SignatureError as e:
        raise Rejected(400, str(e)) from None

    label, covered, sig = None, None, None
    for lb, (cv, sg) in signatures.items():
        if cv.params.get("tag") == "web-bot-auth":
            label, covered, sig = lb, cv, sg
            break
    if label is None:
        raise Rejected(403, 'no signature with tag="web-bot-auth"')

    # Covered components and parameters required by the draft and by our policy
    names = {i.value for i in covered if not i.params}
    # Draft -01 form: Signature-Agent: sig1="https://..." covered as "signature-agent";key="sig1".
    # Older form, still sent by some agents: Signature-Agent: "https://..." covered as "signature-agent".
    legacy = h.get("signature-agent", "").lstrip().startswith('"')
    agent_covered = any(i.value == "signature-agent" and
                        (i.params.get("key") == label if not legacy else not i.params)
                        for i in covered)
    missing = REQUIRED.get(request.method, {"@authority"}) - names
    if missing or not agent_covered:
        need = sorted(missing) + ([] if agent_covered else [f'"signature-agent";key="{label}"'])
        raise Rejected(403, f"signature must also cover {', '.join(need)}",
                       {"Accept-Signature": ACCEPT_SIGNATURE})
    p = covered.params
    for name in ("created", "expires", "keyid"):
        if name not in p:
            raise Rejected(403, f"missing signature parameter {name}")
    now = int(time.time())
    if p["expires"] <= now:
        raise Rejected(403, f"signature expired {now - p['expires']} s ago")
    if p["created"] > now + CLOCK_SKEW or p["expires"] - p["created"] > MAX_LIFETIME:
        raise Rejected(403, f"signature lifetime must be at most {MAX_LIFETIME} s")

    # Resolve Signature-Agent and select the key by (URL, keyid)
    try:
        if legacy:
            item = http_sfv.Item()
            item.parse(h["signature-agent"].encode())
            agent_url = item.value
        else:
            agents = http_sfv.Dictionary()
            agents.parse(h.get("signature-agent", "").encode())
            agent_url = agents[label].value
    except (ValueError, KeyError):
        raise Rejected(400, "Signature-Agent has no member for this signature") from None
    jwk = resolve_directory(agent_url).get(p["keyid"])
    if jwk is None:
        raise Rejected(403, "unverified: keyid not found in the agent's directory")

    try:
        verify(msg, covered, sig, public_key_from_jwk(jwk))
    except SignatureError as e:
        raise Rejected(403, f"invalid: {e}") from None

    if "content-digest" in names:      # the signature covers the header, we check the body
        body = await request.body()
        if h["content-digest"] != content_digest(body):
            raise Rejected(403, "invalid: body does not match Content-Digest")
    return {"agent": agent_url, "keyid": p["keyid"], "covered": sorted(names)}


@app.get("/books/{book_id}")
async def get_book(book_id: int, request: Request):
    bot = await verify_bot(request)
    return {"book": BOOKS.get(book_id), "verified_agent": bot["agent"]}


@app.post("/orders", status_code=201)
async def create_order(request: Request):
    bot = await verify_bot(request)
    order = json.loads(await request.body())
    return {"order": {"id": 5001, **order}, "verified_agent": bot["agent"]}
