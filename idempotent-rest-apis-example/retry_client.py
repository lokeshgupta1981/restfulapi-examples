"""A client that times out after 1 second and retries a POST request.

Start the server with SLOW_CREATE_SECONDS=2 so that every create takes 2 seconds.
Run: python retry_client.py          (no key: every retry creates one more order)
     python retry_client.py --key    (same Idempotency-Key on every attempt: one order)
Then list the orders with: curl -s http://localhost:8000/orders
"""
import json
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000"
TIMEOUT_SECONDS = 1
MAX_ATTEMPTS = 5


def post_order(body, idem_key):
    headers = {"Content-Type": "application/json"}
    if idem_key:
        headers["Idempotency-Key"] = f'"{idem_key}"'  # the IETF draft defines the value as a quoted string
    request = urllib.request.Request(f"{BASE}/orders", data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.status, json.loads(response.read()), response.headers.get("Idempotent-Replayed")


def create_with_retries(body, use_key):
    idem_key = str(uuid.uuid4()) if use_key else None  # one key for all attempts
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            status, order, replayed = post_order(body, idem_key)
            print(f"attempt {attempt}: HTTP {status} {order['id']} replayed={replayed}")
            return order
        except urllib.error.HTTPError as error:
            print(f"attempt {attempt}: HTTP {error.code} {json.loads(error.read())['title']}")
            if error.code != 409:
                raise
        except urllib.error.URLError as error:
            print(f"attempt {attempt}: connection error {error.reason}")
        except TimeoutError:
            print(f"attempt {attempt}: no response after {TIMEOUT_SECONDS} s")
        if attempt < MAX_ATTEMPTS:
            # Exponential backoff with full jitter: wait a random time up to 0.5, 1, 2, 4 seconds.
            delay = random.uniform(0, 0.5 * 2 ** (attempt - 1))
            time.sleep (delay)
    print(f"gave up after {MAX_ATTEMPTS} attempts")
    return None


if __name__ == "__main__":
    create_with_retries({"items": ["chair"]}, use_key="--key" in sys.argv)
