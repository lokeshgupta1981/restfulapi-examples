"""Mistake demo: a stdio server that prints to stdout before the transport starts."""

from mcp.server import MCPServer

mcp = MCPServer("print-demo")

print("Starting print-demo server")  # wrong: stdout carries JSON-RPC messages


@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone by name."""
    return f"Hello, {name}"


if __name__ == "__main__":
    mcp.run()
