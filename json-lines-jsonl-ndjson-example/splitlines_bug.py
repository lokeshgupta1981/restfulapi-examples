"""str.splitlines() also splits on U+2028, which JSON allows inside a string."""
import json

line = json.dumps({"id": "ord_1005", "note": "Gate code\u20281234"}, ensure_ascii=False) + "\n"

print("split('\\n'):", [json.loads(part)["id"] for part in line.split("\n") if part])
try:
    print([json.loads(part) for part in line.splitlines()])
except json.JSONDecodeError as err:
    print("splitlines():", err)
