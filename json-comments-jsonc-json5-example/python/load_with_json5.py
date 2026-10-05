"""Loads the JSONC and the JSON5 file with the json5 package, then writes strict JSON."""
import json
from pathlib import Path

import json5

CONFIG = Path(__file__).resolve().parent.parent / "config"

for name in ["orders-service.jsonc", "orders-service.json5"]:
    text = (CONFIG / name).read_text(encoding="utf-8")
    settings = json5.loads(text)
    print(f"{name}: {settings}")

# What we send to another program is always strict JSON.
settings = json5.loads((CONFIG / "orders-service.json5").read_text(encoding="utf-8"))
print(json.dumps(settings))
