"""A demo facilitator with the x402 v2 interface: POST /verify and POST /settle.

A real facilitator checks an EIP-3009 or Solana authorization and settles it onchain. This one
checks an Ed25519 signature over the authorization and moves balances in memory, so the
handshake runs without a blockchain.

Run: uvicorn facilitator:app --host 127.0.0.1 --port 8001
"""

import json
import time

from cryptography.exceptions import InvalidSignature
from fastapi import FastAPI, Request

from demo_wallets import PUBLIC_KEYS, STARTING_BALANCES

app = FastAPI()
balances = dict(STARTING_BALANCES)
used_nonces: set[str] = set()


def check(body: dict) -> tuple[bool, str | None, str | None]:
    payload, required = body["paymentPayload"], body["paymentRequirements"]
    auth = payload.get("payload", {}).get("authorization", {})
    payer = auth.get("from")
    if payload.get("x402Version") != 2:
        return False, "invalid_x402_version", payer
    accepted = payload.get("accepted", {})
    if (accepted.get("scheme"), accepted.get("network")) != (required["scheme"], required["network"]):
        return False, "invalid_scheme", payer
    if auth.get("to") != required["payTo"] or auth.get("value") != required["amount"]:
        return False, "invalid_payload", payer
    if payer not in PUBLIC_KEYS:
        return False, "invalid_payload", payer
    message = json.dumps(auth, sort_keys=True).encode()
    try:
        PUBLIC_KEYS[payer].verify(bytes.fromhex(payload["payload"]["signature"]), message)
    except (InvalidSignature, ValueError):
        return False, "invalid_payload", payer
    now = int(time.time())
    if not int(auth["validAfter"]) <= now <= int(auth["validBefore"]):
        return False, "invalid_payload", payer
    if auth["nonce"] in used_nonces:
        return False, "invalid_transaction_state", payer  # the same authorization was already settled
    if balances[payer] < int(auth["value"]):
        return False, "insufficient_funds", payer
    return True, None, payer


@app.post("/verify")
async def verify(request: Request):
    ok, reason, payer = check(await request.json())
    return {"isValid": ok, "payer": payer} if ok else {"isValid": False, "invalidReason": reason, "payer": payer}


@app.post("/settle")
async def settle(request: Request):
    body = await request.json()
    ok, reason, payer = check(body)
    network = body["paymentRequirements"]["network"]
    if not ok:
        return {"success": False, "errorReason": reason, "transaction": "", "network": network, "payer": payer}
    auth = body["paymentPayload"]["payload"]["authorization"]
    used_nonces.add(auth["nonce"])
    balances[payer] -= int(auth["value"])
    balances[auth["to"]] = balances.get(auth["to"], 0) + int(auth["value"])
    return {"success": True, "transaction": f"demo-tx-{auth['nonce'][:12]}", "network": network,
            "payer": payer, "amount": auth["value"]}
