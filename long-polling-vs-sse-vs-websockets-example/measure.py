"""Runs one client per technique at the same time, publishes the same events,
and prints delivery latency, requests and bytes on the wire for each one.

Each client goes through its own small TCP proxy that counts the bytes in
both directions (HTTP headers, SSE framing, WebSocket frames, everything).

Usage:  python measure.py [events] [gap_seconds] [idle_seconds]
Env:    NETWORK_DELAY_MS=50  adds 50 ms in each direction (default 0)
        WS_DEFLATE=1         lets the WebSocket client negotiate permessage-deflate
"""

import asyncio
import json
import os
import statistics
import sys
import time

import httpx
import websockets

SERVER_HOST, SERVER_PORT = "127.0.0.1", 9150
BASE = f"http://{SERVER_HOST}:{SERVER_PORT}"
ORDER = f"/orders/run-{int(time.time())}"   # a new order per run, so old events are not replayed
PROXY_PORTS = {"long polling": 9152, "SSE": 9153, "WebSocket": 9154}
DELAY = float(os.getenv("NETWORK_DELAY_MS", "0")) / 1000   # one-way delay added by the proxy
WS_COMPRESSION = "deflate" if os.getenv("WS_DEFLATE") == "1" else None


class CountingProxy:
    def __init__(self, port: int) -> None:
        self.port = port
        self.up = 0        # client -> server bytes
        self.down = 0      # server -> client bytes
        self.connections = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", self.port)

    async def handle(self, client_reader, client_writer) -> None:
        self.connections += 1
        server_reader, server_writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)

        async def pipe(reader, writer, direction):
            # Forward bytes after a fixed delay to act like a slower network.
            queue: asyncio.Queue = asyncio.Queue()

            async def deliver():
                while (item := await queue.get()) is not None:
                    due, data = item
                    await asyncio.sleep (max(0.0, due - time.monotonic()))
                    writer.write(data)
                    await writer.drain()
                writer.close()

            sender = asyncio.create_task(deliver())
            try:
                while data := await reader.read(65536):
                    if direction == "up":
                        self.up += len(data)
                    else:
                        self.down += len(data)
                    queue.put_nowait((time.monotonic() + DELAY, data))
            except ConnectionError:
                pass
            finally:
                queue.put_nowait(None)
                await sender

        await asyncio.gather(
            pipe(client_reader, server_writer, "up"),
            pipe(server_reader, client_writer, "down"),
            return_exceptions=True,
        )


class Result:
    def __init__(self) -> None:
        self.latencies_ms: list[float] = []
        self.requests = 0

    def got(self, event: dict) -> None:
        self.latencies_ms.append((time.time() - event["sent_at"]) * 1000)


async def long_poll_client(port: int, result: Result, stop: asyncio.Event) -> None:
    last_id = 0
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=40) as client:
        while not stop.is_set():
            response = await client.get(f"{ORDER}/updates", params={"after": last_id})
            result.requests += 1
            body = response.json()
            for event in body["events"]:
                result.got(event)
            last_id = body["last_id"]


async def sse_client(port: int, result: Result, stop: asyncio.Event) -> None:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", f"http://127.0.0.1:{port}{ORDER}/stream") as response:
            result.requests += 1
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    result.got(json.loads(line[len("data: "):]))
                if stop.is_set():
                    return


async def websocket_client(port: int, result: Result, stop: asyncio.Event) -> None:
    async with websockets.connect(f"ws://127.0.0.1:{port}{ORDER}/socket", compression=WS_COMPRESSION) as socket:
        result.requests += 1
        while not stop.is_set():
            try:
                message = await asyncio.wait_for(socket.recv(), 1)
            except TimeoutError:
                continue
            result.got(json.loads(message))


def snapshot(proxies):
    return {name: (p.up, p.down) for name, p in proxies.items()}


async def main(count: int, gap: float, idle: float) -> None:
    proxies = {name: CountingProxy(port) for name, port in PROXY_PORTS.items()}
    for proxy in proxies.values():
        await proxy.start()
    results = {name: Result() for name in proxies}
    stop = asyncio.Event()
    clients = [
        asyncio.create_task(long_poll_client(PROXY_PORTS["long polling"], results["long polling"], stop)),
        asyncio.create_task(sse_client(PROXY_PORTS["SSE"], results["SSE"], stop)),
        asyncio.create_task(websocket_client(PROXY_PORTS["WebSocket"], results["WebSocket"], stop)),
    ]
    await asyncio.sleep (1)   # let all three clients connect
    start = snapshot(proxies)
    start_requests = {name: r.requests for name, r in results.items()}

    async with httpx.AsyncClient(base_url=BASE) as publisher:
        for n in range(count):
            await publisher.post(f"{ORDER}/events", json={"status": f"step-{n + 1}"})
            await asyncio.sleep (gap)
    await asyncio.sleep (1)
    busy = snapshot(proxies)
    busy_requests = {name: r.requests for name, r in results.items()}

    print(f"{count} events, one every {gap * 1000:.0f} ms, network delay {DELAY * 1000:.0f} ms each way")
    print(f"{'technique':<14}{'received':>9}{'p50 ms':>8}{'max ms':>8}{'requests':>10}{'bytes down':>12}{'bytes up':>10}")
    for name, result in results.items():
        lat = result.latencies_ms
        up = busy[name][0] - start[name][0]
        down = busy[name][1] - start[name][1]
        requests = busy_requests[name] - start_requests[name]
        print(f"{name:<14}{len(lat):>9}{statistics.median(lat):>8.1f}{max(lat):>8.1f}"
              f"{requests:>10}{down:>12}{up:>10}")

    if idle > 0:
        await asyncio.sleep (idle)
        end = snapshot(proxies)
        print(f"\nIdle for {idle:.0f} s with no events")
        print(f"{'technique':<14}{'requests':>10}{'bytes down':>12}{'bytes up':>10}")
        for name, result in results.items():
            print(f"{name:<14}{result.requests - busy_requests[name]:>10}"
                  f"{end[name][1] - busy[name][1]:>12}{end[name][0] - busy[name][0]:>10}")

    stop.set()
    for task in clients:
        task.cancel()


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(
        int(args[0]) if len(args) > 0 else 20,
        float(args[1]) if len(args) > 1 else 0.5,
        float(args[2]) if len(args) > 2 else 0,
    ))
