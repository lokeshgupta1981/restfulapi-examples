"""Build and check an OpenAI Batch API input file (JSONL) from orders.jsonl."""
import json
import os
from pathlib import Path

MAX_REQUESTS = 50_000
MAX_BYTES = 200 * 1024 * 1024

source = Path("data/orders.jsonl")
target = Path("data/batch-input.jsonl")

with source.open(encoding="utf-8") as orders, target.open("w", encoding="utf-8", newline="\n") as out:
    for line in orders:
        order = json.loads(line)
        request = {
            "custom_id": order["id"],
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": os.environ.get("BATCH_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "Write a one-sentence shipping update."},
                    {"role": "user", "content": json.dumps(order, ensure_ascii=False)},
                ],
                "max_tokens": 60,
            },
        }
        out.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")

# Check the file before uploading it with purpose="batch".
seen_ids = set()
with target.open(encoding="utf-8") as batch:
    for line_no, line in enumerate(batch, start=1):
        request = json.loads(line)
        if set(request) != {"custom_id", "method", "url", "body"}:
            raise ValueError(f"line {line_no}: wrong keys")
        if request["custom_id"] in seen_ids:
            raise ValueError(f"line {line_no}: duplicate custom_id")
        seen_ids.add(request["custom_id"])

size = target.stat().st_size
if len(seen_ids) > MAX_REQUESTS or size > MAX_BYTES:
    raise ValueError(f"{len(seen_ids)} requests and {size} bytes exceed the batch limits")
print(f"{target}: {len(seen_ids)} requests, {size} bytes, custom_id values unique")
