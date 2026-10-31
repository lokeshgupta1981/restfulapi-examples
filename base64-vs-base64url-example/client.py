"""Follow the legacy (standard Base64) cursor with httpx, twice.

1. The cursor is glued into the URL string: '+' arrives as a space.
2. The cursor is passed with params=: httpx percent-encodes it.

Start the server first: uvicorn server:app --host 127.0.0.1 --port 9170
Run: python3 client.py
"""

import os

import httpx

API = os.environ.get("API_URL", "http://127.0.0.1:9170")

with httpx.Client(base_url=API) as client:
    cursor = client.get("/legacy/orders").json()["next_cursor"]
    print("next_cursor:", cursor)

    glued = client.get(f"/legacy/orders?cursor={cursor}")
    print("\n1. URL built with an f-string")
    print("   sent  :", glued.request.url)
    print("   status:", glued.status_code, glued.json()["detail"])

    encoded = client.get("/legacy/orders", params={"cursor": cursor})
    print("\n2. URL built with params=")
    print("   sent  :", encoded.request.url)
    print("   status:", encoded.status_code, [o["id"] for o in encoded.json()["items"]])

    url_safe = client.get("/orders").json()["next_cursor"]
    plain = client.get(f"/orders?cursor={url_safe}")
    print("\n3. Base64URL cursor in an f-string")
    print("   sent  :", plain.request.url)
    print("   status:", plain.status_code, [o["id"] for o in plain.json()["items"]])
