"""Random order IDs stop guessing, but not BOLA: the vulnerable API still serves a leaked ID."""
import secrets

from fastapi.testclient import TestClient

import vulnerable_app

ALICE = {"Authorization": "Bearer demo-token-alice"}  # fake demo token
db = vulnerable_app.db

# Give every order a random 62-bit ID instead of 1001, 1002, ...
for (old_id,) in db.execute("SELECT id FROM orders").fetchall():
    new_id = secrets.randbits(62)
    db.execute("UPDATE orders SET id = ? WHERE id = ?", (new_id, old_id))
    db.execute("UPDATE reviews SET order_id = ? WHERE order_id = ?", (new_id, old_id))

client = TestClient(vulnerable_app.app)

hits = sum(client.get(f"/orders/{secrets.randbits(62)}", headers=ALICE).status_code == 200
           for _ in range(10_000))
print(f"Random guesses that hit an order: {hits} of 10000")

review = client.get("/books/978-0141439587/reviews").json()[0]
print(f"Public review by {review['author']} links to order {review['order_id']}")

r = client.get(f"/orders/{review['order_id']}", headers=ALICE)
print(f"Alice reads it: HTTP {r.status_code} {r.json()}")
