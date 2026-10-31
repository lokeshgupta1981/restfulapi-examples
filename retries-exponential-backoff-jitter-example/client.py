"""Runs the retry helper against server.py. Usage: python client.py [503|429|404|post-naive|post-no-key|post]"""
import sys
import time
import uuid

import httpx

from retry import request_with_retry

BASE = "http://127.0.0.1:8000"


def main(scenario: str) -> None:
    with httpx.Client(base_url=BASE, timeout=1.0) as client:
        if scenario == "503":
            r = request_with_retry(client, "GET", "/orders/1001?fail=2")
        elif scenario == "429":
            r = request_with_retry(client, "GET", "/reports/sales")
        elif scenario == "404":
            r = request_with_retry(client, "GET", "/orders/9999")
        elif scenario in ("post-naive", "post-no-key"):
            before = len(client.get("/orders").json())
            try:                             # post-naive is the mistake: retrying a POST without a key
                r = request_with_retry(client, "POST", "/orders?slow=2", json={"book": "REST in Practice"},
                                       retry_unsafe=scenario == "post-naive")
            except httpx.TimeoutException as exc:
                print("raised", type(exc).__name__)
                r = None
            time.sleep(2.5)                  # let the server finish the last slow request
            print("new orders on the server:", len(client.get("/orders").json()) - before)
        elif scenario == "post":
            key = str(uuid.uuid4())
            before = len(client.get("/orders").json())
            r = request_with_retry(client, "POST", "/orders?slow=2", json={"book": "REST in Practice"},
                                   headers={"Idempotency-Key": key})
            time.sleep(2.5)
            print("new orders on the server:", len(client.get("/orders").json()) - before)
        else:
            sys.exit(__doc__)
        if r is not None:
            print(r.status_code, r.text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "503")
