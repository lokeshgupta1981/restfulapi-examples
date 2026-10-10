"""The order-desk server over Streamable HTTP at http://127.0.0.1:8000/mcp."""
import logging
import sys

from mcp.server import MCPServer

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")

mcp = MCPServer("order-desk")


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Return the shipping status of one order."""
    return f"Order {order_id} shipped on 2026-10-08."


if __name__ == "__main__":
    # Binds to 127.0.0.1 only, as the spec recommends for a local server.
    mcp.run("streamable-http", host="127.0.0.1", port=8000)
