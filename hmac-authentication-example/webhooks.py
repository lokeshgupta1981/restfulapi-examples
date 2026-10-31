"""Webhook signatures: the GitHub test vector, a Stripe-style signature checked by the
official stripe library, and why re-serialized JSON breaks both."""
import hashlib
import hmac
import json
import time

import stripe

# --- 1. GitHub: X-Hub-Signature-256 is the HMAC of the raw body, nothing else
github_secret = b"It's a Secret to Everybody"  # test value from the GitHub docs
payload = b"Hello, World!"
expected = "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
computed = "sha256=" + hmac.new(github_secret, payload, hashlib.sha256).hexdigest()
print("GitHub:", computed)
print("matches the GitHub docs:", hmac.compare_digest(computed, expected))

# --- 2. Stripe: Stripe-Signature: t=<timestamp>,v1=<HMAC of "<timestamp>.<raw body>">
stripe_secret = "whsec_demo_not_a_real_secret"  # example value
event = b'{"id":"evt_demo","type":"payment_intent.succeeded"}'


def stripe_header(body: bytes, timestamp: int) -> str:
    signed = str(timestamp).encode() + b"." + body
    v1 = hmac.new(stripe_secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={v1}"


def stripe_check(label, body, header):
    try:
        stripe.WebhookSignature.verify_header(body.decode(), header, stripe_secret, tolerance=300)
        print(label + ": accepted")
    except stripe.SignatureVerificationError as error:
        print(label + ": rejected (" + str(error) + ")")


now = int(time.time())
print()
print("Stripe-Signature:", stripe_header(event, now))
stripe_check("fresh event", event, stripe_header(event, now))
stripe_check("event signed 10 minutes ago", event, stripe_header(event, now - 600))
reserialized = json.dumps(json.loads(event)).encode()
stripe_check("re-serialized body", reserialized, stripe_header(event, now))

# --- 3. Why: json.dumps() writes different bytes for the same data
raw = b'{"item":"keyboard","quantity":2}'
print()
print(raw.decode())
print(json.dumps(json.loads(raw)))
print("same bytes:", raw == json.dumps(json.loads(raw)).encode())
