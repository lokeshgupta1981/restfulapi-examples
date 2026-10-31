"""Demo token issuer for the Orders API.

  POST /token                    issues a signed JWT; body {"sub": "alice", "alg": "RS256"}
  GET  /.well-known/jwks.json    public keys (RS256 and ES256) for verifiers
  POST /rotate                   creates a new RS256 key; new tokens use it, the old key stays published

HS256 tokens are signed with the shared secret from the HS256_SECRET environment variable
(hex). The asymmetric keys are created in memory at startup. All keys are demo keys.
"""
import os
import time
import uuid
from datetime import datetime, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import FastAPI, HTTPException
from jwt.algorithms import ECAlgorithm, RSAAlgorithm
from pydantic import BaseModel

ISSUER = os.environ.get("ISSUER_URL", "http://127.0.0.1:8000")
AUDIENCE = "orders-api"
HS256_SECRET = bytes.fromhex(os.environ["HS256_SECRET"])  # shared with orders_api.py
HS256_KID = "hs-demo-1"


def new_kid(prefix):
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6]}"


# kid -> (private key, alg). Only the newest RS256 key signs; older ones stay in the JWKS.
signing_keys = {}
current = {}


def add_key(alg):
    if alg == "RS256":
        key, kid = rsa.generate_private_key(public_exponent=65537, key_size=2048), new_kid("rsa")
    else:
        key, kid = ec.generate_private_key(ec.SECP256R1()), new_kid("ec")
    signing_keys[kid] = (key, alg)
    current[alg] = kid
    return kid


add_key("RS256")
add_key("ES256")

app = FastAPI()


class TokenRequest(BaseModel):
    sub: str
    alg: str = "RS256"


@app.post("/token")
def issue(req: TokenRequest):
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": req.sub, "aud": AUDIENCE, "scope": "orders:read",
              "iat": now, "exp": now + 300}
    if req.alg == "HS256":
        kid, key = HS256_KID, HS256_SECRET
    elif req.alg in current:
        kid = current[req.alg]
        key = signing_keys[kid][0]
    else:
        raise HTTPException(400, f"unsupported alg {req.alg}")
    token = jwt.encode(claims, key, algorithm=req.alg, headers={"kid": kid})
    return {"access_token": token, "token_type": "Bearer", "expires_in": 300}


@app.get("/.well-known/jwks.json")
def jwks():
    keys = []
    for kid, (key, alg) in signing_keys.items():
        algo = RSAAlgorithm if alg == "RS256" else ECAlgorithm
        jwk = algo.to_jwk(key.public_key(), as_dict=True)
        jwk.update({"kid": kid, "alg": alg, "use": "sig"})
        keys.append(jwk)
    return {"keys": keys}


@app.post("/rotate")
def rotate():
    old = current["RS256"]
    return {"old_kid": old, "new_kid": add_key("RS256")}
