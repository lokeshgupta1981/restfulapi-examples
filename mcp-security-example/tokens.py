"""Mint test access tokens for the demo server.

A real MCP server gets tokens from an OAuth authorization server and checks them with
the server's public keys. This demo signs tokens with a shared test secret (HS256) so
it runs without an authorization server. Never use a shared secret like this in production.

Example:
  python tokens.py --sub alice --scope "cart:write"
  python tokens.py --sub alice --scope "cart:write" --aud https://api.example.com
"""

import argparse
import os
import time

import jwt

SECRET = os.environ.get("DEMO_TOKEN_SECRET", "dev-only-secret-change-me-0123456789")


def mint(sub: str, scope: str, aud: str = "http://127.0.0.1:8000/mcp", ttl: int = 600) -> str:
    now = int(time.time())
    claims = {"iss": "http://127.0.0.1:9000", "sub": sub, "aud": aud,
              "scope": scope, "iat": now, "exp": now + ttl}
    return jwt.encode(claims, SECRET, algorithm="HS256")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sub", required=True)
    parser.add_argument("--scope", default="")
    parser.add_argument("--aud", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--ttl", type=int, default=600)
    options = parser.parse_args()
    print(mint(options.sub, options.scope, options.aud, options.ttl))
