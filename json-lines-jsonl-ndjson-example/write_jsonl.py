"""Write orders to a JSON Lines file, one compact JSON object per line."""
import json
from pathlib import Path

orders = [
    {"id": "ord_1001", "customer": "Ana", "total": 42.5, "status": "paid"},
    {"id": "ord_1002", "customer": "Bo", "total": 18.0, "status": "pending"},
    {"id": "ord_1003", "customer": "Chloé", "total": 99.9, "status": "paid",
     "note": "Leave at the door.\nRing twice."},
]

path = Path("data/orders.jsonl")
path.parent.mkdir(exist_ok=True)

with path.open("w", encoding="utf-8", newline="\n") as out:
    for order in orders:
        line = json.dumps(order, ensure_ascii=False, separators=(",", ":"))
        out.write(line + "\n")

# Appending a record later does not touch the existing lines.
new_order = {"id": "ord_1004", "customer": "Dev", "total": 7.25, "status": "paid"}
with path.open("a", encoding="utf-8", newline="\n") as out:
    out.write(json.dumps(new_order, ensure_ascii=False, separators=(",", ":")) + "\n")

print(f"wrote {path} ({path.stat().st_size} bytes)")
