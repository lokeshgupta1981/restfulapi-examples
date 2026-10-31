"""Monthly request charges for REST APIs and HTTP APIs in US East (N. Virginia).

Prices from https://aws.amazon.com/api-gateway/pricing/ (read 2026-10-31):
  REST API: first 333 million requests $3.50/million, next 667 million $2.80/million,
            then $2.38/million (the page's examples go up to 15 billion).
  HTTP API: first 300 million requests $1.00/million, then $0.90/million.
            HTTP API requests are metered in 512 KB increments.
Only request charges: no free tier, caching, data transfer or Lambda costs.
Usage: python pricing.py 1000000 5000000 100000000 1000000000
"""

import math
import sys

REST_TIERS = [(333e6, 3.50), (667e6, 2.80), (math.inf, 2.38)]
HTTP_TIERS = [(300e6, 1.00), (math.inf, 0.90)]
METER_KB = 512


def cost(requests, tiers):
    total, left = 0.0, requests
    for size, price in tiers:
        used = min(left, size)
        total += used / 1e6 * price
        left -= used
        if left <= 0:
            break
    return total


def http_metered(requests, payload_kb):
    """An HTTP API request larger than 512 KB counts as several requests."""
    return requests * max(1, math.ceil(payload_kb / METER_KB))


if __name__ == "__main__":
    volumes = [int(x) for x in sys.argv[1:]] or [1_000_000, 5_000_000, 100_000_000, 1_000_000_000]
    print(f"{'requests/month':>15} {'REST API':>12} {'HTTP API':>12} {'HTTP saves':>11}")
    for n in volumes:
        rest, http = cost(n, REST_TIERS), cost(n, HTTP_TIERS)
        print(f"{n:>15,} {rest:>12,.2f} {http:>12,.2f} {1 - http / rest:>10.0%}")

    print("\nHTTP API with large payloads (5,000,000 calls):")
    for kb in (10, 512, 600, 2048):
        metered = http_metered(5_000_000, kb)
        print(f"  {kb:>5} KB payload -> {metered:>12,} metered requests -> ${cost(metered, HTTP_TIERS):,.2f}")

    print("\nCheck against the pricing page examples:")
    print(f"  HTTP 432 million  -> ${cost(432e6, HTTP_TIERS):,.2f} (page: $418.80)")
    print(f"  REST 5 million    -> ${cost(5e6, REST_TIERS):,.2f} (page: $17.50)")
