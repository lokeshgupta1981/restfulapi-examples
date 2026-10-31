"""Reads every order by following next_cursor until has_more is false.

Run (server on port 8000): python client.py
"""
import os

import httpx

BASE = os.environ.get("BASE", "http://localhost:8000")

with httpx.Client(base_url=BASE) as client:
    params = {"limit": 4}
    page_no, total = 0, 0
    while True:
        body = client.get("/orders", params=params).raise_for_status().json()
        page_no += 1
        total += len(body["data"])
        print(f"page {page_no}: {[o['id'] for o in body['data']]}")
        if not body["has_more"]:
            break
        params["cursor"] = body["next_cursor"]
    print(f"{total} orders in {page_no} requests")
