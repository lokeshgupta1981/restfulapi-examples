"""Orders API Lambda handler that works behind both API Gateway API types.

- REST API (Lambda proxy integration) sends the payload format 1.0 event.
- HTTP API (PayloadFormatVersion 2.0) sends the payload format 2.0 event.

The handler reads both shapes and always returns the full proxy response
(statusCode, headers, body as a string), which both API types accept.
Orders live in memory, so this is a demo, not a real store.
"""

import base64
import json

ORDERS = {
    "1001": {"id": "1001", "book": "REST in Practice", "quantity": 1, "status": "SHIPPED"},
}
_next_id = 1002


def parse_request(event):
    """Return (method, path, path_params, body_text, caller) for a 1.0 or 2.0 event."""
    if event.get("version") == "2.0":
        method = event["requestContext"]["http"]["method"]
        path = event["rawPath"]
        claims = event["requestContext"].get("authorizer", {}).get("jwt", {}).get("claims", {})
        caller = "jwt:" + claims["sub"] if "sub" in claims else "anonymous"
    else:
        method = event["httpMethod"]
        path = event["path"]
        api_key_id = event["requestContext"].get("identity", {}).get("apiKeyId")
        caller = "api-key:" + api_key_id if api_key_id else "anonymous"

    body = event.get("body")
    if body and event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return method, path, event.get("pathParameters") or {}, body, caller


def response(status, payload):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
        "isBase64Encoded": False,
    }


def handler(event, context):
    global _next_id
    method, path, params, body, caller = parse_request(event)
    print(json.dumps({"format": event.get("version", "1.0"), "method": method,
                      "path": path, "caller": caller}))

    if method == "GET" and "orderId" in params:
        order = ORDERS.get(params["orderId"])
        if order is None:
            return response(404, {"error": "order not found", "orderId": params["orderId"]})
        return response(200, order)

    if method == "POST" and path.endswith("/orders"):
        try:
            data = json.loads(body or "")
        except json.JSONDecodeError:
            return response(400, {"error": "body must be JSON"})
        if not isinstance(data, dict) or not data.get("book") or not isinstance(data.get("quantity"), int):
            return response(400, {"error": "book (string) and quantity (integer) are required"})
        order = {"id": str(_next_id), "book": data["book"],
                 "quantity": data["quantity"], "status": "NEW", "createdBy": caller}
        ORDERS[order["id"]] = order
        _next_id += 1
        return response(201, order)

    return response(404, {"error": "no route", "method": method, "path": path})
