"""Sends 3 parallel calls to each tool of blocking_server.py and times them."""

import asyncio
import time

from mcp import Client

URL = "http://127.0.0.1:8041/mcp"


async def call_once(tool: str) -> None:
    async with Client(URL) as client:
        await client.call_tool(tool, {})


async def main() -> None:
    for tool in ["blocking_in_async", "awaited_in_async", "blocking_in_sync"]:
        start = time.perf_counter()
        await asyncio.gather(*(call_once(tool) for _ in range(3)))
        print(f"{tool}: 3 parallel calls took {time.perf_counter() - start:.1f} s")


asyncio.run(main())
