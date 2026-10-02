"""List the tools of the orders MCP server and call two of them.

python try_client.py         -> starts orders_mcp.py over stdio
python try_client.py http    -> connects to http://127.0.0.1:8000/mcp
"""
import asyncio
import json
import sys

from mcp import Client, StdioServerParameters


async def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        server = "http://127.0.0.1:8000/mcp"
    else:
        server = StdioServerParameters(command=sys.executable, args=["orders_mcp.py"])

    async with Client(server) as client:
        print("protocol:", client.protocol_version)

        tools = await client.list_tools()
        for tool in tools.tools:
            print("tool:", tool.name, "-", tool.description.splitlines()[0])

        result = await client.call_tool("find_orders", {"status": "pending"})
        print("find_orders:", json.dumps(result.structured_content))

        result = await client.call_tool("cancel_order", {"order_id": "ord_1001"})
        print("cancel_order: is_error =", result.is_error)
        print("  ", result.content[0].text)


asyncio.run(main())
