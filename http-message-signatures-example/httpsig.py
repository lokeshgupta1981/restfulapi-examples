"""A small, readable RFC 9421 (HTTP Message Signatures) implementation for Ed25519.

It covers what the article needs: derived components (@method, @authority,
@path, @query, @target-uri, @scheme), header fields, the ;key= parameter for
Dictionary header members, the ;req parameter for signing a request component
in a response, the signature base, signing, and verifying.
"""
import base64
import hashlib
import json
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import http_sfv
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


# ---------- small helpers ----------

def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def content_digest(body: bytes) -> str:
    """Content-Digest header value (RFC 9530) with SHA-256."""
    return "sha-256=:" + base64.b64encode(hashlib.sha256(body).digest()).decode() + ":"


def jwk_thumbprint(jwk: dict) -> str:
    """JWK SHA-256 thumbprint of an Ed25519 key (RFC 7638, RFC 8037 A.3)."""
    canonical = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"]},
        separators=(",", ":"), sort_keys=True,
    )
    return b64url_encode(hashlib.sha256(canonical.encode()).digest())


def private_key_from_jwk(jwk: dict) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(b64url_decode(jwk["d"]))


def public_key_from_jwk(jwk: dict) -> Ed25519PublicKey:
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise ValueError("only Ed25519 keys are supported")
    return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))


# ---------- the message we sign or verify ----------

@dataclass
class Message:
    """A request (method + url) or a response (status). Header names are lowercase."""
    method: str = ""
    url: str = ""
    status: int = 0
    headers: dict = field(default_factory=dict)
    request: "Message | None" = None  # for responses: the request they answer


class SignatureError(Exception):
    pass


def _derived(name: str, msg: Message) -> str:
    parts = urlsplit(msg.url)
    if name == "@method":
        return msg.method.upper()
    if name == "@authority":
        return parts.netloc.lower()
    if name == "@scheme":
        return parts.scheme.lower()
    if name == "@path":
        return parts.path or "/"
    if name == "@query":
        return "?" + parts.query
    if name == "@target-uri":
        return msg.url
    if name == "@status":
        return str(msg.status)
    raise SignatureError(f"unsupported derived component {name}")


def component_value(item: http_sfv.Item, msg: Message) -> str:
    """The value of one covered component, as it appears in the signature base."""
    name = item.value
    if "req" in item.params:          # take the value from the request, not the response
        if msg.request is None:
            raise SignatureError(f"{name};req needs the request")
        msg = msg.request
    if name.startswith("@"):
        return _derived(name, msg)
    if name not in msg.headers:
        raise SignatureError(f"covered header {name} is missing")
    raw = msg.headers[name]
    if "key" in item.params:          # one member of a Dictionary header
        d = http_sfv.Dictionary()
        d.parse(raw.encode())
        key = item.params["key"]
        if key not in d:
            raise SignatureError(f"{name} has no member {key}")
        return str(d[key])
    return raw.strip()


def signature_base(covered: http_sfv.InnerList, msg: Message) -> str:
    """Section 2.5 of RFC 9421: one line per component, then @signature-params."""
    lines = []
    for item in covered:
        ident = str(http_sfv.Item(item.value)) + str(item.params)
        lines.append(f"{ident}: {component_value(item, msg)}")
    lines.append(f'"@signature-params": {covered}')
    return "\n".join(lines)


def build_covered(components, params) -> http_sfv.InnerList:
    """components: ["@method", ("signature-agent", {"key": "sig1"})], params: ordered dict."""
    covered = http_sfv.InnerList()
    for c in components:
        name, cparams = (c, {}) if isinstance(c, str) else c
        item = http_sfv.Item(name)
        for k, v in cparams.items():
            item.params[k] = v
        covered.append(item)
    for k, v in params.items():
        covered.params[k] = v
    return covered


def sign(msg, label, components, params, private_key):
    """Returns (signature_base, Signature-Input value, Signature value)."""
    covered = build_covered(components, params)
    base = signature_base(covered, msg)
    sig = private_key.sign(base.encode("ascii"))
    sig_input = f"{label}={covered}"
    signature = f"{label}=:{base64.b64encode(sig).decode()}:"
    return base, sig_input, signature


def parse_signatures(msg: Message) -> dict:
    """Returns {label: (covered InnerList, signature bytes)}; raises on malformed headers."""
    try:
        inputs = http_sfv.Dictionary()
        inputs.parse(msg.headers["signature-input"].encode())
        sigs = http_sfv.Dictionary()
        sigs.parse(msg.headers["signature"].encode())
    except KeyError as e:
        raise SignatureError(f"missing header {e.args[0]}") from None
    except ValueError as e:
        raise SignatureError(f"malformed signature header: {e}") from None
    result = {}
    for label, covered in inputs.items():
        if label in sigs:
            result[label] = (covered, sigs[label].value)
    return result


def verify(msg, covered, sig, public_key) -> str:
    """Rebuilds the signature base from the received message and checks the signature."""
    base = signature_base(covered, msg)
    try:
        public_key.verify(sig, base.encode("ascii"))
    except Exception:
        raise SignatureError("signature does not match") from None
    return base
