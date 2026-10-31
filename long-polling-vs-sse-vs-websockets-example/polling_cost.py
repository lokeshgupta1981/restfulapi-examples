"""Compares plain polling with long polling for an order that changes rarely.

Both clients run at the same time for DURATION seconds while the script
publishes a few status changes. The plain polling client asks every
POLL_INTERVAL seconds with wait=0 (the server answers at once, even when
nothing changed). The long polling client uses the default wait, so the
server holds each request until an event arrives.

Each client goes through its own byte-counting proxy from measure.py.

Usage:  python polling_cost.py [duration_seconds] [poll_interval_seconds]
"""

import asyncio
import statistics
import sys
import time

import httpx

from measure import BASE, ORDER, CountingProxy, Result

PLAIN_PORT, LONG_PORT = 9157, 9158
PUBLISH_AT = [7.3, 25.1, 41.8]   # seconds after the start: three status changes
STATUSES = ["packed", "shipped", "out_for_delivery"]


class Counter(Result):
    def __init__(self) -> None:
        super().__init__()
        self.empty = 0


async def poll_client(port: int, wait: float | None, interval: float,
                      result: Counter, stop: asyncio.Event) -> None:
    last_id = 0
    params = {} if wait is None else {"wait": wait}
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=40) as client:
        while not stop.is_set():
            response = await client.get(f"{ORDER}/updates", params={"after": last_id, **params})
            result.requests += 1
            body = response.json()
            if not body["events"]:
                result.empty += 1
            for event in body["events"]:
                result.got(event)
            last_id = body["last_id"]
            if interval:
                await asyncio.sleep(interval)


async def main(duration: float, interval: float) -> None:
    proxies = {"plain polling": CountingProxy(PLAIN_PORT), "long polling": CountingProxy(LONG_PORT)}
    for proxy in proxies.values():
        await proxy.start()
    results = {name: Counter() for name in proxies}
    stop = asyncio.Event()
    clients = [
        asyncio.create_task(poll_client(PLAIN_PORT, 0, interval, results["plain polling"], stop)),
        asyncio.create_task(poll_client(LONG_PORT, None, 0, results["long polling"], stop)),
    ]

    start = time.monotonic()
    async with httpx.AsyncClient(base_url=BASE) as publisher:
        for at, status in zip(PUBLISH_AT, STATUSES):
            await asyncio.sleep(max(0.0, start + at - time.monotonic()))
            await publisher.post(f"{ORDER}/events", json={"status": status})
    await asyncio.sleep(max(0.0, start + duration - time.monotonic()))
    stop.set()

    print(f"{duration:.0f} s, {len(PUBLISH_AT)} events, plain polling every {interval:g} s")
    print(f"{'technique':<15}{'received':>9}{'requests':>10}{'empty':>7}"
          f"{'p50 ms':>9}{'max ms':>9}{'bytes total':>13}")
    for name, result in results.items():
        lat = result.latencies_ms
        proxy = proxies[name]
        print(f"{name:<15}{len(lat):>9}{result.requests:>10}{result.empty:>7}"
              f"{statistics.median(lat):>9.1f}{max(lat):>9.1f}{proxy.up + proxy.down:>13}")

    for task in clients:
        task.cancel()


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(
        float(args[0]) if len(args) > 0 else 60,
        float(args[1]) if len(args) > 1 else 2,
    ))
