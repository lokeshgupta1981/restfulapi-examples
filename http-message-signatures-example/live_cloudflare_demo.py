"""Sends signed requests to Cloudflare Research's public Web Bot Auth demo server.

The demo server checks for an Ed25519 signature made with the RFC 9421 B.1.4 test
key, so this script uses that published TEST key (never trusted in production).
It tries the Signature-Agent dictionary form (draft-ietf-webbotauth-httpsig-protocol-01)
and the older plain-string form, and prints the verdict line from the page.
Needs internet access.
"""
import json
import re
import time

import httpx

from httpsig import Message, jwk_thumbprint, private_key_from_jwk, sign

URL = "https://http-message-signatures-example.research.cloudflare.com/"
AGENT = "https://http-message-signatures-example.research.cloudflare.com"

with open("keys/rfc9421-test-key-ed25519.json") as f:
    TEST_KEY = json.load(f)
private_key = private_key_from_jwk(TEST_KEY)

forms = {
    "dictionary form (draft -01)": (f'sig1="{AGENT}"', ("signature-agent", {"key": "sig1"})),
    "plain string form (older drafts)": (f'"{AGENT}"', "signature-agent"),
}
for name, (agent_header, agent_component) in forms.items():
    now = int(time.time())
    msg = Message(method="GET", url=URL, headers={"signature-agent": agent_header})
    _, sig_input, signature = sign(
        msg, "sig1", ["@authority", agent_component],
        {"created": now, "expires": now + 60, "keyid": jwk_thumbprint(TEST_KEY),
         "alg": "ed25519", "tag": "web-bot-auth"},
        private_key,
    )
    r = httpx.get(URL, timeout=15, headers={
        "Signature-Agent": agent_header, "Signature-Input": sig_input, "Signature": signature})
    text = re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<style.*?</style>", "", r.text))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    verdict = next(line for line in lines if re.search(r"authenticated|validate|support", line))
    print(f"{name}: HTTP {r.status_code}, {r.headers.get('date')}")
    print(f"  Signature-Agent: {agent_header}")
    print(f"  page says: {verdict}")
