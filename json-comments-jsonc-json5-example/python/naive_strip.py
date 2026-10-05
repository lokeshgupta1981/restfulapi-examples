"""A regex that deletes everything after // also deletes part of a URL.
The json5 parser reads the same file correctly."""
import json
import re
from pathlib import Path

import json5

CONFIG = Path(__file__).resolve().parent.parent / "config"
text = (CONFIG / "orders-service.jsonc").read_text(encoding="utf-8")

# Wrong: the regex does not know whether // is inside a string.
naive = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # block comments
naive = re.sub(r"//.*", "", naive)                  # line comments
print([line for line in naive.splitlines() if "paymentUrl" in line][0])
try:
    json.loads(naive)
except json.JSONDecodeError as error:
    print(f"{type(error).__name__}: {error}")

# Right: a parser that understands comments and strings.
settings = json5.loads(text)
print("json5:", settings["paymentUrl"])
