"""Retry an API call after HTTP 502, 503 or 504, only when a retry is safe."""
import random
import sys
import time

import httpx

RETRYABLE_STATUS = {502, 503, 504}
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


def wait_seconds(response, attempt):
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None and retry_after.isdigit():
        return int(retry_after)
    # Exponential backoff with full jitter: 0-0.5 s, 0-1 s, 0-2 s, ...
    return random.uniform(0, 0.5 * 2 ** attempt)


def send_with_retry(client, method, url, max_attempts=4, **kwargs):
    headers = kwargs.get("headers") or {}
    retry_allowed = method in IDEMPOTENT_METHODS or "Idempotency-Key" in headers
    for attempt in range(max_attempts):
        response = client.request(method, url, **kwargs)
        print(f"attempt {attempt + 1}: {method} {url} -> {response.status_code}")
        last_attempt = attempt == max_attempts - 1
        if response.status_code not in RETRYABLE_STATUS or not retry_allowed or last_attempt:
            return response
        delay = wait_seconds(response, attempt)
        print(f"  waiting {delay:.2f} s before the next attempt")
        time.sleep (delay)
    return response


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8503"
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        payment_response = send_with_retry(client, "POST", "/orders/1001/payments", json={"amount": "49.90"})
        print(payment_response.status_code, payment_response.headers.get("Content-Type"))
        order_response = send_with_retry(client, "GET", "/orders/1001")
        print(order_response.text)
