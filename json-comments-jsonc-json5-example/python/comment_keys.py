"""The costs of "_comment" and "//" keys in plain JSON."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

CONFIG = Path(__file__).resolve().parent.parent / "config"
text = (CONFIG / "orders-service-comment-keys.json").read_text(encoding="utf-8")

# 1. The duplicate "//" keys: the parser keeps only the last one.
settings = json.loads(text)
print("Keys after parsing:", list(settings))
print('Value of "//":', settings["//"])

# 2. A strict schema rejects the extra keys.
schema = json.loads((CONFIG / "orders-service.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)
for error in validator.iter_errors(settings):
    print("Schema error:", error.message)

# 3. A program that rewrites the file keeps the last "//" only.
print(json.dumps(settings, indent=2))
