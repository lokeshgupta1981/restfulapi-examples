"""A small MCP server for an order desk.

The ORDER_DESK_FAULT environment variable turns on one common mistake.
  none         logs to stderr only (correct, the default)
  stdout       prints a startup message to stdout (breaks stdio)
  missing-key  exits when ORDER_API_KEY is not set
  slow         the tool waits 5 seconds before it answers
"""
import logging
import os
import sys
import time

from mcp.server import MCPServer

FAULT = os.environ.get("ORDER_DESK_FAULT", "none")

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("order-desk")

if FAULT == "stdout":
    # The bug: plain text on stdout, with no newline after it
    print("Loading order cache... ", end="", flush=True)

if FAULT == "missing-key" and not os.environ.get("ORDER_API_KEY"):
    log.error("ORDER_API_KEY is not set, exiting")
    sys.exit(1)

mcp = MCPServer("order-desk")


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Return the shipping status of one order."""
    log.info("get_order_status %s", order_id)
    if FAULT == "slow":
        time.sleep (5)
    return f"Order {order_id} shipped on 2026-10-08."


if __name__ == "__main__":
    log.info("order-desk ready (fault=%s)", FAULT)
    mcp.run("stdio")
