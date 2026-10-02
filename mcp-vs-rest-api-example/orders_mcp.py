"""MCP server that wraps the Orders REST API.

Run over stdio:            python orders_mcp.py
Run over Streamable HTTP:  python orders_mcp.py http
"""
import os
import sys
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

API_BASE = os.environ.get("ORDERS_API_URL", "http://127.0.0.1:8080")

mcp = MCPServer("orders")


class Order(BaseModel):
    id: str
    customer: str
    status: str
    total: float


async def call_api(method: str, path: str, params: dict | None = None):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as http:
        resp = await http.request(method, path, params=params)
    if resp.status_code >= 400:
        # ToolError passes this text to the model. Other exceptions are hidden.
        detail = resp.json().get("detail", resp.text)
        raise ToolError(f"HTTP {resp.status_code}: {detail}")
    return resp.json()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def find_orders(
    status: Literal["pending", "shipped", "cancelled"] | None = None,
    customer: Annotated[str | None, Field(description="Customer name, for example Asha")] = None,
) -> list[Order]:
    """Find orders. Both filters are optional."""
    params = {k: v for k, v in {"status": status, "customer": customer}.items() if v}
    return [Order(**o) for o in await call_api("GET", "/orders", params)]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_order(order_id: str) -> Order:
    """Get one order by its id, for example ord_1002."""
    return Order(**await call_api("GET", f"/orders/{order_id}"))


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
async def cancel_order(order_id: str) -> Order:
    """Cancel a pending order. Shipped orders cannot be cancelled.
    Ask the user to confirm before calling this tool."""
    return Order(**await call_api("POST", f"/orders/{order_id}/cancel"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
