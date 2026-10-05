"""Shows what the standard json module does with comments and trailing commas."""
import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config"

for name in ["orders-service.jsonc", "trailing-comma.jsonc"]:
    text = (CONFIG / name).read_text(encoding="utf-8")
    try:
        json.loads(text)
    except json.JSONDecodeError as error:
        print(f"{name}: {type(error).__name__}: {error}")
