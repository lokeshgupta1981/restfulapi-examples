"""The web shop asks for the least scope first and more only when it needs it.

On HTTP 403 with error="insufficient_scope", it reads the scope the API asks
for, gets a new token with that scope added, and retries the request once.

Usage: python client.py
"""
import os
import re

import httpx

from oauth_client import fetch_token

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001")


def challenge_params(header):
    """Parse the parameters of a Bearer challenge into a dict."""
    return dict(re.findall(r'(\w+)="([^"]*)"', header))


class ShopClient:
    def __init__(self, user, scopes):
        self.user, self.scopes = user, set(scopes)
        self.token = self.new_token()

    def new_token(self):
        result = fetch_token("bookshop-web", None, self.user, " ".join(sorted(self.scopes)))
        self.scopes = set(result["scope"].split())  # keep what was GRANTED
        print(f"  token granted with scope: {result['scope']}")
        return result["access_token"]

    def call(self, method, path, **kwargs):
        for attempt in (1, 2):
            response = httpx.request(method, API_URL + path,
                                     headers={"Authorization": f"Bearer {self.token}"}, **kwargs)
            print(f"  {method} {path} -> {response.status_code}")
            params = challenge_params(response.headers.get("www-authenticate", ""))
            if response.status_code != 403 or params.get("error") != "insufficient_scope":
                return response
            needed = set(params.get("scope", "").split())
            if attempt == 2 or needed <= self.scopes:
                return response  # asking again would not help
            print(f"  API asks for scope: {' '.join(sorted(needed))}")
            self.scopes |= needed
            self.token = self.new_token()
            if not needed <= self.scopes:
                print("  not granted, so we stop instead of retrying")
                return response
        return response


if __name__ == "__main__":
    print("Sign in asha with read-only scopes:")
    shop = ShopClient("asha", {"books:read", "orders:read"})
    shop.call("GET", "/orders")
    print("Asha places an order:")
    r = shop.call("POST", "/orders", json={"book": "b-2"})
    print(f"  body: {r.text}")
    print("Asha tries a refund (only staff may grant orders:refund):")
    r = shop.call("POST", "/orders/o-1001/refund")
    print(f"  body: {r.text}")
