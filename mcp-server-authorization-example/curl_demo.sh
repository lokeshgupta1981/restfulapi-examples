#!/usr/bin/env bash
# Walks through MCP authorization with curl. Start auth_server.py and mcp_server.py first.
set -e

echo "== 1. Call a tool without a token"
curl -s -i http://127.0.0.1:9410/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/call" -H "Mcp-Name: list_orders" \
  -d @requests/list_orders.json
echo; echo

echo "== 2. Protected resource metadata (RFC 9728)"
curl -s http://127.0.0.1:9410/.well-known/oauth-protected-resource/mcp | python -m json.tool
echo

echo "== 3. Authorization server metadata (RFC 8414)"
curl -s http://127.0.0.1:9420/.well-known/oauth-authorization-server | python -m json.tool
echo

echo "== 4. Get a token for this MCP server with scope orders:read"
TOKEN=$(python get_token.py http://127.0.0.1:9410/mcp "orders:read")
echo

echo "== 5. Call list_orders with the token"
curl -s -i http://127.0.0.1:9410/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/call" -H "Mcp-Name: list_orders" \
  -d @requests/list_orders.json
echo; echo

echo "== 6. Call cancel_order with the same token"
curl -s -i http://127.0.0.1:9410/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/call" -H "Mcp-Name: cancel_order" \
  -d @requests/cancel_order.json
echo; echo

echo "== 7. Send a token issued for another API (the reports API)"
OTHER_TOKEN=$(python get_token.py http://127.0.0.1:9430/reports "reports:read" 2>/dev/null)
curl -s -i http://127.0.0.1:9410/mcp \
  -H "Authorization: Bearer $OTHER_TOKEN" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "Mcp-Method: tools/call" -H "Mcp-Name: list_orders" \
  -d @requests/list_orders.json
echo
