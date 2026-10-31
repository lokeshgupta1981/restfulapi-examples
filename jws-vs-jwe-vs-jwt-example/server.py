"""Orders API that accepts three kinds of tokens on three routes."""
import os

import uvicorn
from fastapi import FastAPI, Header, HTTPException

import tokens as t

app = FastAPI(title="Orders API")

ORDERS = {"user-42": [{"id": "ord-1001", "total": 59.90}],
          "admin": [{"id": "ord-0001", "total": 12999.00}]}


def bearer(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    return authorization.removeprefix("Bearer ")


def check(read, token):
    try:
        return read(token)
    except Exception as e:
        raise HTTPException(401, f"invalid token: {type(e).__name__}",
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})


def answer(claims):
    return {"user": claims["sub"], "email": claims["email"], "scope": claims["scope"],
            "orders": ORDERS.get(claims["sub"], [])}


@app.get("/jws/orders")
def orders_with_jws(authorization: str | None = Header(None)):
    return answer(check(t.verify_jws, bearer(authorization)))


@app.get("/jwe-only/orders")
def orders_with_decrypt_only(authorization: str | None = Header(None)):
    """Deliberately naive: decrypts and trusts the claims. Do not copy."""
    return answer(check(t.decrypt_only, bearer(authorization)))


@app.get("/orders")
def orders_with_nested(authorization: str | None = Header(None)):
    return answer(check(t.decrypt_and_verify, bearer(authorization)))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
