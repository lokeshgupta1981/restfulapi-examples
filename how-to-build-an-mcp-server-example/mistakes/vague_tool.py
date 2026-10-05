"""Mistake demo: prints the definition a model sees for a vague tool."""

import asyncio
import json

from mcp import Client
from mcp.server import MCPServer

mcp = MCPServer("vague-demo")


@mcp.tool()
def tasks(p: str, s: str = "") -> list[dict]:
    """Get tasks."""
    return []


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = tools.tools[0]
        print(json.dumps({"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}, indent=2))


asyncio.run(main())
