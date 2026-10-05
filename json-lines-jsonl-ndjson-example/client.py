"""Read a streamed JSONL response line by line with requests."""
import json
import time

import requests

start = time.monotonic()
with requests.get("http://127.0.0.1:9387/orders/export", stream=True, timeout=10) as response:
    response.raise_for_status()
    print("Content-Type:", response.headers["Content-Type"])
    for line in response.iter_lines(decode_unicode=False):
        if not line:
            continue
        order = json.loads(line)
        elapsed = time.monotonic() - start
        print(f"{elapsed:4.1f}s {order['id']} {order['status']}")
