"""Calls print_server.py over stdio and shows what the client reports."""

import asyncio
import sys

from mcp import Client, StdioServerParameters


async def main() -> None:
    server = StdioServerParameters(command=sys.executable, args=["print_server.py"])
    async with Client(server) as client:
        result = await client.call_tool("hello", {"name": "Ana"})
        print(result.content[0].text)


asyncio.run(main())
