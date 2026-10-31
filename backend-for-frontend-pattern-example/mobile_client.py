"""Plays the mobile app: signs in, then loads the order screen twice.

1. directly from the three general-purpose services (no BFF)
2. from the mobile BFF in one request

It prints the number of requests and the JSON bytes each way.
    python mobile_client.py [order_id]
"""
import base64
import hashlib
import json
import secrets
import sys
from urllib.parse import parse_qs, urlparse

import httpx

import settings


def sign_in(http: httpx.Client) -> str:
    """Authorization code flow with PKCE, as a public client (no secret)."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = "com.example.bookstore:/callback"
    r = http.get(f"{settings.AUTH_URL}/authorize", params={
        "response_type": "code", "client_id": settings.MOBILE_CLIENT_ID, "redirect_uri": redirect,
        "state": "xyz", "code_challenge": challenge, "code_challenge_method": "S256"})
    code = parse_qs(urlparse(r.headers["location"]).query)["code"][0]
    r = http.post(f"{settings.AUTH_URL}/token", data={
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "redirect_uri": redirect, "client_id": settings.MOBILE_CLIENT_ID})
    return r.json()["access_token"]


def main():
    order_id = sys.argv[1] if len(sys.argv) > 1 else "1001"
    with httpx.Client() as http:
        auth = {"Authorization": f"Bearer {sign_in(http)}"}

        print("--- Without a BFF: the app calls every service itself")
        calls, size = 0, 0

        def get(url, headers=None):
            nonlocal calls, size
            r = http.get(url, headers=headers or {})
            calls, size = calls + 1, size + len(r.content)
            print(f"GET {urlparse(url).path:<20} -> {r.status_code}, {len(r.content):>5} bytes")
            return r.json()

        order = get(f"{settings.ORDERS_URL}/orders/{order_id}", auth)
        for line in order["lines"]:
            get(f"{settings.CATALOG_URL}/books/{line['bookId']}")
        get(f"{settings.SHIPPING_URL}/shipments/{order['shipmentId']}", auth)
        print(f"Total: {calls} requests, {size} bytes of JSON")

        print("\n--- With the mobile BFF: one request")
        r = http.get(f"{settings.MOBILE_BFF_URL}/mobile/v1/order-screen/{order_id}", headers=auth)
        print(f"GET /mobile/v1/order-screen/{order_id} -> {r.status_code}, {len(r.content)} bytes")
        print(json.dumps(r.json(), indent=2))


if __name__ == "__main__":
    main()
