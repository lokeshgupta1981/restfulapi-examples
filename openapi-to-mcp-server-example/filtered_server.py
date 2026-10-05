"""Generated MCP server with two filters: no admin operations and no DELETE.

Run over stdio:  python filtered_server.py
"""
import os
from pathlib import Path

import httpx2
import yaml
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

spec = yaml.safe_load((Path(__file__).parent / "openapi.yaml").read_text())

api_client = httpx2.AsyncClient(
    base_url=os.environ.get("HELPDESK_API_URL", spec["servers"][0]["url"]),
    headers={"Authorization": f"Bearer {os.environ['HELPDESK_API_TOKEN']}"},
    timeout=10,
)

mcp = FastMCP.from_openapi(
    openapi_spec=spec,
    client=api_client,
    name="helpdesk-filtered",
    route_maps=[
        RouteMap(tags={"admin"}, mcp_type=MCPType.EXCLUDE),
        RouteMap(methods=["DELETE"], mcp_type=MCPType.EXCLUDE),
    ],
    mcp_names={"listTickets": "list_tickets", "getTicket": "get_ticket"},
)

if __name__ == "__main__":
    mcp.run(show_banner=False)
