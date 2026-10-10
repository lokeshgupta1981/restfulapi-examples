"""The same order service as an MCP server (stdio). Run: python orders_mcp_server.py"""
import logging
import sys
from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import orders_core

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
mcp = MCPServer("orders")

Status = Literal["open", "paid", "shipped", "cancelled"]


@mcp.tool()
def list_orders(
    customer_id: str | None = None,
    status: Status | None = None,
    fields: list[str] | None = None,
) -> list[dict]:
    """List orders, optionally filtered by customer ID (for example C-5) and status.
    Pass fields, for example ["id", "total"], to return only those fields."""
    orders = orders_core.list_orders(customer_id, status)
    if fields:
        orders = [{f: o[f] for f in fields} for o in orders]
    return orders


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Return one order with its items, total and shipping address."""
    try:
        return orders_core.get_order(order_id)
    except KeyError as err:
        raise ToolError(err.args[0]) from err


@mcp.tool()
def cancel_order(order_id: str, reason: str) -> dict:
    """Cancel an open or paid order. Shipped and cancelled orders cannot be cancelled."""
    try:
        return orders_core.cancel_order(order_id, reason)
    except (KeyError, ValueError) as err:
        # ToolError sends the message to the model. Other exceptions are hidden by the SDK.
        raise ToolError(err.args[0]) from err


if __name__ == "__main__":
    mcp.run("stdio")
