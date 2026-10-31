"""Retry an HTTP call with capped exponential backoff, full jitter and Retry-After support."""
import random
from time import monotonic
from time import sleep as pause
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 8.0) -> float:
    """Full jitter: a random wait between 0 and the capped exponential value."""
    return random.uniform(0, min(cap, base * 2 ** attempt))


def retry_after_seconds(response: httpx.Response) -> float | None:
    """Reads Retry-After as seconds ("120") or as an HTTP date."""
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    if value.strip().isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def request_with_retry(client: httpx.Client, method: str, url: str, *, max_attempts: int = 5,
                       base: float = 0.5, cap: float = 8.0, max_retry_after: float = 30.0,
                       retry_unsafe: bool = False, log=print, **kwargs) -> httpx.Response:
    headers = kwargs.get("headers") or {}
    can_retry = method in IDEMPOTENT_METHODS or "Idempotency-Key" in headers or retry_unsafe
    start = monotonic()

    for attempt in range(max_attempts):
        response, error = None, None
        try:
            response = client.request(method, url, **kwargs)
            outcome = str(response.status_code)
            if response.status_code not in RETRYABLE_STATUS:
                log(f"{monotonic() - start:6.2f}s  attempt {attempt + 1}: {outcome}, done")
                return response
        except httpx.TransportError as exc:          # connection refused, reset, timeout
            error, outcome = exc, type(exc).__name__

        last = attempt == max_attempts - 1
        if not can_retry or last:
            reason = "not safe to retry" if not can_retry else "no attempts left"
            log(f"{monotonic() - start:6.2f}s  attempt {attempt + 1}: {outcome}, {reason}")
            if response is not None:
                return response
            raise error

        wait = retry_after_seconds(response) if response is not None else None
        source = "Retry-After"
        if wait is None:
            wait, source = backoff_delay(attempt, base, cap), "backoff"
        elif wait > max_retry_after:
            log(f"{monotonic() - start:6.2f}s  attempt {attempt + 1}: {outcome}, "
                f"Retry-After {wait:.0f}s is too long, giving up")
            return response
        log(f"{monotonic() - start:6.2f}s  attempt {attempt + 1}: {outcome}, "
            f"waiting {wait:.2f}s ({source})")
        pause(wait)
