"""Times the order screen: the app calling the services directly vs one BFF call.

Both paths use the same pattern: the order first, then books and shipment in
parallel. Each path runs RUNS times after a warm-up; we print the median.
    python bench.py [runs]
"""
import asyncio
import statistics
import sys
import time

import httpx

import settings
from mobile_client import sign_in

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 50


async def direct(http, auth):
    order = (await http.get(f"{settings.ORDERS_URL}/orders/1001", headers=auth)).json()
    calls = [http.get(f"{settings.CATALOG_URL}/books/{l['bookId']}") for l in order["lines"]]
    calls.append(http.get(f"{settings.SHIPPING_URL}/shipments/{order['shipmentId']}", headers=auth))
    await asyncio.gather(*calls)


async def via_bff(http, auth):
    r = await http.get(f"{settings.MOBILE_BFF_URL}/mobile/v1/order-screen/1001", headers=auth)
    r.raise_for_status()


async def median_ms(fn, http, auth):
    for _ in range(5):
        await fn(http, auth)  # warm-up: open connections, first-call costs
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        await fn(http, auth)
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


async def main():
    with httpx.Client() as sync_http:
        auth = {"Authorization": f"Bearer {sign_in(sync_http)}"}
    async with httpx.AsyncClient() as http:
        d = await median_ms(direct, http, auth)
        b = await median_ms(via_bff, http, auth)
    print(f"SIM_DELAY_MS={settings.SIM_DELAY_MS}, runs={RUNS}")
    print(f"direct from the app (4 requests): median {d:6.1f} ms")
    print(f"through the mobile BFF (1 request): median {b:6.1f} ms")


asyncio.run(main())
