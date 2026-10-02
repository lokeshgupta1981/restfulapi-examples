"""Simulate an AI agent that sends several LLM calls at once and obeys Retry-After.

python agent_client.py [parallel_calls]
"""
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

GATEWAY = "http://127.0.0.1:8080/v1/chat/completions"
HEADERS = {"Authorization": "Bearer key-free"}
START = time.monotonic()


def log(msg: str) -> None:
    print(f"[{time.monotonic() - START:5.1f}s] {msg}", flush=True)


def ask(task: int) -> bool:
    body = {"messages": [{"role": "user", "content": f"Task {task}: summarize the open orders."}],
            "max_tokens": 500}
    with httpx.Client(timeout=60) as http:
        for attempt in range(1, 4):
            resp = http.post(GATEWAY, json=body, headers=HEADERS)
            h = resp.headers
            if resp.status_code == 200:
                log(f"task {task}: 200, reserved {h['x-tokens-reserved']}, used {h['x-tokens-used']}, "
                    f"remaining {h['x-ratelimit-remaining-tokens']}")
                return True
            if resp.status_code not in (429, 503) or attempt == 3:
                break
            # Wait as long as the server asks, plus a little jitter so that
            # parallel retries do not all arrive at the same moment.
            wait = int(h.get("Retry-After", "5")) + random.random()
            log(f"task {task}: {resp.status_code}, remaining {h.get('x-ratelimit-remaining-tokens')}, "
                f"retry in {wait:.1f}s")
            threading.Event().wait(wait)  # wait without busy looping
    log(f"task {task}: gave up with HTTP {resp.status_code}")
    return False


n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
with ThreadPoolExecutor(max_workers=n) as pool:
    results = list(pool.map(ask, range(1, n + 1)))
print(f"{sum(results)} of {n} tasks succeeded")
