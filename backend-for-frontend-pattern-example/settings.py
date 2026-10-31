"""Ports, URLs and demo keys shared by every process in the example.

Every value can be overridden with an environment variable, so the demo can run
on any free ports. The keys below are FAKE DEMO VALUES. Never reuse them.
"""
import os

AUTH_PORT = int(os.getenv("AUTH_PORT", "8000"))
ORDERS_PORT = int(os.getenv("ORDERS_PORT", "8001"))
CATALOG_PORT = int(os.getenv("CATALOG_PORT", "8002"))
SHIPPING_PORT = int(os.getenv("SHIPPING_PORT", "8003"))
MOBILE_BFF_PORT = int(os.getenv("MOBILE_BFF_PORT", "8004"))
WEB_BFF_PORT = int(os.getenv("WEB_BFF_PORT", "8005"))

AUTH_URL = f"http://127.0.0.1:{AUTH_PORT}"
ORDERS_URL = f"http://127.0.0.1:{ORDERS_PORT}"
CATALOG_URL = f"http://127.0.0.1:{CATALOG_PORT}"
SHIPPING_URL = f"http://127.0.0.1:{SHIPPING_PORT}"
MOBILE_BFF_URL = f"http://127.0.0.1:{MOBILE_BFF_PORT}"
WEB_BFF_URL = f"http://127.0.0.1:{WEB_BFF_PORT}"

# FAKE DEMO KEY: signs the demo access tokens (HS256). A real authorization
# server signs with a private key and publishes the public key (JWKS).
TOKEN_SIGNING_KEY = "demo-only-signing-key-not-a-secret-0001"

# FAKE DEMO SECRET: the web BFF is a confidential OAuth client.
WEB_BFF_CLIENT_ID = "bookstore-web-bff"
WEB_BFF_CLIENT_SECRET = "demo-only-client-secret"

# The mobile app is a public client: it has no secret and relies on PKCE.
MOBILE_CLIENT_ID = "bookstore-mobile"

# Simulated work inside each downstream service (database, other calls).
SIM_DELAY_MS = int(os.getenv("SIM_DELAY_MS", "80"))

# Access token lifetime in seconds (short, so the refresh can be shown).
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_TTL", "300"))
