"""Mistake demo: a blocking call inside an async tool stalls every other request."""

import time

import anyio

from mcp.server import MCPServer

mcp = MCPServer("blocking-demo")


@mcp.tool()
async def blocking_in_async() -> str:
    """Wrong: time.sleep blocks the event loop."""
    time.sleep (1)
    return "done"


@mcp.tool()
async def awaited_in_async() -> str:
    """Right: await a non-blocking call."""
    await anyio.sleep (1)
    return "done"


@mcp.tool()
def blocking_in_sync() -> str:
    """Right: the SDK runs a plain def tool in a worker thread."""
    time.sleep (1)
    return "done"


if __name__ == "__main__":
    mcp.run("streamable-http", host="127.0.0.1", port=8041)
