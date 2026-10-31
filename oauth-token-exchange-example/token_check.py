"""Access token validation shared by the Orders API and the Payments API."""
import os

import jwt
from fastapi import HTTPException, Request

AUTH_URL = os.environ.get("AUTH_URL", "http://127.0.0.1:8000")
JWKS = jwt.PyJWKClient(AUTH_URL + "/jwks")


def require_token(request: Request, audience: str, scope: str) -> dict:
    """Return the claims of a valid bearer token for this API, or raise 401/403."""
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    token = header[7:]
    try:
        key = JWKS.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"],
                            issuer=AUTH_URL, audience=audience)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, f"invalid token: {exc}",
                            headers={"WWW-Authenticate":
                                     f'Bearer error="invalid_token", '
                                     f'error_description="{exc}"'})
    if scope not in claims.get("scope", "").split():
        raise HTTPException(403, f"scope {scope} required",
                            headers={"WWW-Authenticate":
                                     f'Bearer error="insufficient_scope", scope="{scope}"'})
    return claims
