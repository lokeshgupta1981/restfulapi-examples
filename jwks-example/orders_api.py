"""Orders API (resource server) that verifies JWT access tokens with the issuer's JWKS.

At start-up it reads the issuer's metadata to find jwks_uri. It never takes a key
URL from the token itself. PyJWKClient caches the JWK Set for JWKS_CACHE_SECONDS
and refreshes it once when it sees an unknown kid (at most once per 30 seconds).
"""
import os
import time

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ISSUER = os.environ.get("ISSUER", "http://127.0.0.1:8000")
AUDIENCE = "orders-api"
CACHE_SECONDS = float(os.environ.get("JWKS_CACHE_SECONDS", "300"))
STARTED = time.monotonic()

metadata = httpx.get(f"{ISSUER}/.well-known/oauth-authorization-server").json()
JWKS_URI = metadata["jwks_uri"]


class LoggingJWKClient(jwt.PyJWKClient):
    """PyJWKClient that counts and logs every real HTTP fetch of the JWKS."""
    fetches = 0

    def fetch_data(self):
        data = super().fetch_data()
        LoggingJWKClient.fetches += 1
        kids = [k.get("kid") for k in data["keys"]]
        print(f"[orders-api t={time.monotonic() - STARTED:5.1f}s] "
              f"JWKS fetch #{self.fetches}: kids={kids}", flush=True)
        return data


jwks_client = LoggingJWKClient(JWKS_URI, lifespan=CACHE_SECONDS)


def verify_access_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)  # picks the key by kid
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256", "ES256"],  # never let the token choose freely
        audience=AUDIENCE,
        issuer=ISSUER,
    )


app = FastAPI()


@app.get("/orders")
def list_orders(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse({"error": "invalid_request"}, status_code=401,
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = verify_access_token(auth.removeprefix("Bearer "))
    except jwt.PyJWTError as e:
        return JSONResponse(
            {"error": "invalid_token", "error_description": str(e)}, status_code=401,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    return {"client": claims["sub"], "orders": [{"id": 1042, "total": 250}]}


@app.get("/debug/jwks-fetches")
def jwks_fetches():
    return {"fetches": LoggingJWKClient.fetches}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("API_PORT", "8001")),
                log_level="warning")
