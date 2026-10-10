#!/usr/bin/env bash
# Sends one correct request and eight broken ones to the order-desk HTTP server.
# Start the server first: python servers/http_server.py
URL=http://127.0.0.1:8000/mcp
META='"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}'
LIST='{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{'$META'}}'

probe() {
  local title=$1; shift
  echo "== $title"
  curl -s -o /tmp/probe_body.txt -w "HTTP %{http_code}\n" "$@"
  head -c 220 /tmp/probe_body.txt; echo; echo
}

probe "1. correct request" $URL \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" -d "$LIST"

probe "2. Accept lists only application/json" $URL \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" -d "$LIST"

probe "3. MCP-Protocol-Version header does not match _meta" $URL \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" \
  -d "$(echo "$LIST" | sed 's/2026-07-28/2025-11-25/')"

probe "4. version the server does not support" $URL \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2027-01-01" -H "Mcp-Method: tools/list" \
  -d "$(echo "$LIST" | sed 's/2026-07-28/2027-01-01/')"

probe "5. request without _meta" $URL \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

probe "6. Origin header from another site" $URL -H "Origin: https://evil.example" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" -d "$LIST"

probe "7. GET on the MCP endpoint" $URL -H "Accept: text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28"

probe "8. wrong path (old HTTP+SSE URL)" http://127.0.0.1:8000/sse \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/list" -d "$LIST"

probe "9. method the server does not have" $URL \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: orders/list" \
  -d "$(echo "$LIST" | sed 's#tools/list#orders/list#')"
