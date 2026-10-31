"""Checks the backoff and Retry-After helpers. Run: python test_retry.py"""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx

from retry import backoff_delay, retry_after_seconds

# Full jitter stays between 0 and min(cap, base * 2 ** attempt)
for attempt, limit in [(0, 0.5), (1, 1.0), (2, 2.0), (3, 4.0), (4, 8.0), (10, 8.0)]:
    waits = [backoff_delay(attempt) for _ in range(10_000)]
    assert 0 <= min(waits) and max(waits) <= limit
    print(f"attempt {attempt + 1}: waits from {min(waits):.3f} to {max(waits):.3f} s (limit {limit} s)")

# Retry-After as seconds, as an HTTP date, and missing
assert retry_after_seconds(httpx.Response(429, headers={"Retry-After": "120"})) == 120
in_30s = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
seconds = retry_after_seconds(httpx.Response(503, headers={"Retry-After": in_30s}))
assert 28 <= seconds <= 30, seconds
assert retry_after_seconds(httpx.Response(503)) is None
print(f"Retry-After: {in_30s} -> {seconds:.1f} s")
print("all checks passed")
