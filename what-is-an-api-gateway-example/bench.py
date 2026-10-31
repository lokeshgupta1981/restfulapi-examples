"""Measures the cost of the extra hop: the same GET, direct to the service and through the gateway.

Usage: python bench.py [requests] (bench.sh starts everything)
"""
import os
import statistics
import sys
import time

import httpx

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
GW = os.environ.get("GATEWAY_PORT", "8000")
BP = os.environ.get("BOOKS_PORT", "8001")
KEY = {"X-API-Key": "demo-key-partner-456"}  # demo key; bench.sh raises its limit


def run(url, headers):
    times = []
    with httpx.Client() as c:   # keep-alive, like a real client
        for _ in range(50):
            c.get(url, headers=headers)  # warm-up
        for _ in range(N):
            t = time.perf_counter()
            r = c.get(url, headers=headers)
            times.append((time.perf_counter() - t) * 1000)
            assert r.status_code == 200, r.status_code
    times.sort()
    return statistics.median(times), times[int(len(times) * 0.95)]


direct = run(f"http://127.0.0.1:{BP}/books/1", {})
via = run(f"http://127.0.0.1:{GW}/api/books/1", KEY)
nginx = None
if os.environ.get("NGINX_PORT"):
    nginx = run(f"http://127.0.0.1:{os.environ['NGINX_PORT']}/api/books/1", {})
print(f"{N} sequential GET requests per path, keep-alive, all on localhost")
print(f"direct to books service : median {direct[0]:.2f} ms, p95 {direct[1]:.2f} ms")
print(f"through the gateway     : median {via[0]:.2f} ms, p95 {via[1]:.2f} ms")
if nginx:
    print(f"through plain nginx     : median {nginx[0]:.2f} ms, p95 {nginx[1]:.2f} ms")
print(f"added by gateway.py     : median {via[0]-direct[0]:.2f} ms")
if nginx:
    print(f"added by plain nginx    : median {nginx[0]-direct[0]:.2f} ms")
