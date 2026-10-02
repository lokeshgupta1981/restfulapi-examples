# MCP vs REST API: working example

Companion code for the article [MCP vs REST API: Turning a REST API into an MCP Server](https://restfulapi.net/mcp-vs-rest-api/) on restfulapi.net.
Tested on 2026-10-02 with Python 3.11 and the versions in requirements.txt (MCP protocol 2026-07-28).

## Files
- orders_api.py: small Orders REST API (FastAPI)
- orders_mcp.py: MCP server that wraps the REST API (3 tools)
- try_client.py: test client that lists and calls the tools
- mcp-config.json: config for an MCP host (Claude Code) using the HTTP transport

## Run
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

    # Terminal 1: REST API on port 8080
    uvicorn orders_api:app --port 8080

    # Terminal 2: MCP server on http://127.0.0.1:8000/mcp
    python orders_mcp.py http

    # Terminal 3: test client (HTTP), or without "http" to use stdio
    python try_client.py http

    # Optional: real AI agent (Claude Code)
    claude -p "Which orders are still pending? Then cancel ord_1001." --mcp-config mcp-config.json --strict-mcp-config --allowedTools "mcp__orders__find_orders,mcp__orders__get_order,mcp__orders__cancel_order"
