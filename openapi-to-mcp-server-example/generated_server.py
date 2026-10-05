"""MCP server generated from openapi.yaml: every operation becomes a tool.

Run over stdio:            python generated_server.py
Run over Streamable HTTP:  python generated_server.py http
"""
import os
import sys
from pathlib import Path

import httpx2
import yaml
from fastmcp import FastMCP

spec = yaml.safe_load((Path(__file__).parent / "openapi.yaml").read_text())

# The MCP server calls the API with its own token, read from the environment.
api_client = httpx2.AsyncClient(
    base_url=os.environ.get("HELPDESK_API_URL", spec["servers"][0]["url"]),
    headers={"Authorization": f"Bearer {os.environ['HELPDESK_API_TOKEN']}"},
    timeout=10,
)

mcp = FastMCP.from_openapi(openapi_spec=spec, client=api_client, name="helpdesk-generated")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8001, show_banner=False)
    else:
        mcp.run(show_banner=False)
