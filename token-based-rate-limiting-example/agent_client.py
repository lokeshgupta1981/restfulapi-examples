"""Simulate an AI agent that sends several LLM calls at once and obeys Retry-After.

python agent_client.py [parallel_calls]
"""
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


def ask(task: int) -> None:
    body = {"messages": [{"role": "user", "content": f"Task {task}: summarize the open orders."}],
            "max_tokens": 500}
    with httpx.Client(timeout=60) as http:
        for attempt in range(1, 4):
            resp = http.post(GATEWAY, json=body, headers=HEADERS)
            h = resp.headers
            if resp.status_code == 200:
                log(f"task {task}: 200, reserved {h['x-tokens-reserved']}, used {h['x-tokens-used']}, "
                    f"remaining {h['x-ratelimit-remaining-tokens']}")
                return
            if resp.status_code != 429:
                resp.raise_for_status()
            wait = int(h["Retry-After"])
            log(f"task {task}: 429, remaining {h['x-ratelimit-remaining-tokens']}, retry in {wait}s")
            threading.Event().wait(wait)  # wait without busy looping
    log(f"task {task}: gave up after 3 attempts")


n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
with ThreadPoolExecutor(max_workers=n) as pool:
    pool.map(ask, range(1, n + 1))
