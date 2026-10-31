"""Calls the API with httpx and lets the library build and encode the query string."""

import httpx

with httpx.Client(base_url="http://localhost:8480") as client:
    search = client.get("/products", params={"q": "AT&T"})
    print(search.request.url)
    print(search.json())

    orders = client.get("/orders", params={"status": ["paid", "shipped"], "limit": 2})
    print(orders.request.url)
    print([order["id"] for order in orders.json()["data"]])

    price = client.get("/products/KB-101/price", params={"currency": "INR"})
    print(price.request.url)
    print(price.json())
