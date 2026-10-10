"""Transport-independent MCP logic (protocol version 2026-07-28).

handle() takes one JSON-RPC request and yields the messages to send back:
zero or more notifications, then the response. stdio_server.py and http_server.py
only move these messages, so both transports give the same answers.
"""

import time

PROTOCOL_VERSION = "2026-07-28"
SERVER_INFO = {"name": "orders-demo", "version": "1.0.0"}
ORDERS = {"A-1001": "shipped", "A-1002": "packing"}

TOOLS = [
    {"name": "get_order_status", "description": "Return the status of one order.",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "export_orders", "description": "Export all orders as CSV. Takes a few seconds.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def error(request_id, code: int, message: str, data: dict | None = None) -> dict:
    body = {"code": code, "message": message}
    if data:
        body["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": body}


def result(request_id, payload: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"resultType": "complete", **payload}}


def handle(message: dict):
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params", {})
    meta = params.get("_meta", {})

    # Every request carries its own protocol version; there is no initialize handshake.
    version = meta.get("io.modelcontextprotocol/protocolVersion")
    if version != PROTOCOL_VERSION:
        yield error(request_id, -32022, "Unsupported protocol version",
                    {"supported": [PROTOCOL_VERSION], "requested": version})
        return

    if method == "server/discover":
        yield result(request_id, {"supportedVersions": [PROTOCOL_VERSION], "capabilities": {"tools": {}},
                                  "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO},
                                  "ttlMs": 3600000, "cacheScope": "public"})
        return
    if method == "tools/list":
        yield result(request_id, {"tools": TOOLS, "ttlMs": 300000, "cacheScope": "public"})
        return
    if method != "tools/call":
        yield error(request_id, -32601, "Method not found")
        return

    name = params.get("name")
    args = params.get("arguments", {})
    if name == "get_order_status":
        status = ORDERS.get(args.get("order_id"), "unknown order")
        yield result(request_id, {"content": [{"type": "text", "text": status}], "isError": False})
        return
    if name == "export_orders":
        token = meta.get("progressToken")
        for step in (1, 2, 3):
            time.sleep (0.3)  # stands in for real work
            if token is not None:
                yield {"jsonrpc": "2.0", "method": "notifications/progress",
                       "params": {"progressToken": token, "progress": step, "total": 3,
                                  "message": f"exported part {step} of 3"}}
        csv = "order_id,status\n" + "\n".join(f"{k},{v}" for k, v in ORDERS.items())
        yield result(request_id, {"content": [{"type": "text", "text": csv}], "isError": False})
        return
    yield error(request_id, -32602, f"Unknown tool: {name}")
