"""Create demo access tokens, as an identity provider would after sign-in.

Usage: python tokens.py alice      (prints a token for alice of tenant acme)
       python tokens.py --decode alice
"""
import json
import os
import sys
import time

import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "demo-only-signing-key-not-a-secret")
USERS = {"alice": "acme", "bob": "globex"}


def token_for(user: str, ttl: int = 3600) -> str:
    now = int(time.time())
    claims = {"sub": user, "tenant_id": USERS[user], "aud": "invoices-api",
              "iat": now, "exp": now + ttl}
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


if __name__ == "__main__":
    if sys.argv[1] == "--decode":
        print(json.dumps(jwt.decode(token_for(sys.argv[2]), options={"verify_signature": False}), indent=2))
    else:
        print(token_for(sys.argv[1]))
