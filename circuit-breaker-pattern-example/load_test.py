"""Sends N requests to GET /books/1 with C running at the same time and reports the latency.

Usage: python load_test.py [requests] [concurrency]
"""
import asyncio
import statistics
import sys
import time

import httpx

STORE = "http://127.0.0.1:9600"
INVENTORY = "http://127.0.0.1:9601"


async def main(total, concurrency):
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(f"{INVENTORY}/admin/reset")
        queue = list(range(total))
        latencies, fallbacks = [], 0

        async def worker():
            nonlocal fallbacks
            while queue:
                queue.pop()
                start = time.perf_counter()
                body = (await client.get(f"{STORE}/books/1")).json()
                latencies.append(time.perf_counter() - start)
                if body["in_stock"] is None:
                    fallbacks += 1

        start = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(concurrency)))
        wall = time.perf_counter() - start
        received = (await client.get(f"{INVENTORY}/admin/stats")).json()["requests"]

    latencies.sort()
    print(f"requests sent:              {total} ({concurrency} at a time)")
    print(f"answered with fallback:     {fallbacks}")
    print(f"total time:                 {wall:.2f} s")
    print(f"median latency:             {statistics.median(latencies) * 1000:.0f} ms")
    print(f"slowest request:            {latencies[-1] * 1000:.0f} ms")
    print(f"requests that waited >= 2 s: {sum(1 for x in latencies if x >= 2)}")
    print(f"calls the inventory API got: {received}")


if __name__ == "__main__":
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    asyncio.run(main(total, concurrency))
