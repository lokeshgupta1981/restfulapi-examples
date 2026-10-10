"""An MCP server for a travel agency that exposes all three server primitives (protocol 2026-07-28, stdio).

Tools      get_booking, cancel_booking   (the model decides when to call them)
Resources  docs://policies/cancellation and the template bookings://{booking_id}/receipt
                                          (the client app decides what to read)
Prompts    draft_cancellation_reply      (the user picks it, for example as a slash command)

cancel_booking asks the user for confirmation with form elicitation, sent the 2026-07-28 way:
the server returns an InputRequiredResult and the client retries the call with the answer.

The server reads one JSON-RPC message per line on stdin and writes one per line on stdout.
Run: python3 server.py   (client.py starts it for you)
"""

import base64
import hashlib
import hmac
import json
import re
import sys
import time

PROTOCOL_VERSION = "2026-07-28"
SERVER_INFO = {"name": "travel-desk", "version": "1.0.0"}
STATE_KEY = b"demo-only-secret-change-me"  # protects requestState; load a real key from config
STATE_TTL_SECONDS = 300

BOOKINGS = {
    "B-2041": {"booking_id": "B-2041", "traveler": "Ana Silva", "hotel": "Harbor View Lisbon",
               "check_in": "2026-11-12", "nights": 3, "total_eur": 486.0, "status": "confirmed"},
    "B-2042": {"booking_id": "B-2042", "traveler": "Ravi Menon", "hotel": "Old Town Prague",
               "check_in": "2026-12-01", "nights": 2, "total_eur": 210.0, "status": "confirmed"},
}
POLICY = ("# Cancellation policy\n"
          "- Free cancellation up to 7 days before check-in.\n"
          "- Later cancellations pay one night.\n")

BOOKING_SCHEMA = {
    "type": "object",
    "properties": {"booking_id": {"type": "string"}, "traveler": {"type": "string"},
                   "hotel": {"type": "string"}, "check_in": {"type": "string", "format": "date"},
                   "nights": {"type": "integer"}, "total_eur": {"type": "number"},
                   "status": {"type": "string", "enum": ["confirmed", "cancelled"]}},
    "required": ["booking_id", "hotel", "check_in", "status"],
}
TOOLS = [
    {"name": "get_booking", "title": "Get booking",
     "description": "Return one hotel booking by its id, for example B-2041.",
     "inputSchema": {"type": "object", "properties": {"booking_id": {"type": "string"}},
                     "required": ["booking_id"], "additionalProperties": False},
     "outputSchema": BOOKING_SCHEMA,
     "annotations": {"readOnlyHint": True}},
    {"name": "cancel_booking", "title": "Cancel booking",
     "description": "Cancel a hotel booking. Asks the user to confirm before it changes anything.",
     "inputSchema": {"type": "object", "properties": {"booking_id": {"type": "string"}},
                     "required": ["booking_id"], "additionalProperties": False},
     "annotations": {"destructiveHint": True}},
]
RESOURCES = [
    {"uri": "docs://policies/cancellation", "name": "cancellation-policy", "title": "Cancellation policy",
     "mimeType": "text/markdown", "annotations": {"audience": ["user", "assistant"], "priority": 0.8}},
]
TEMPLATES = [
    {"uriTemplate": "bookings://{booking_id}/receipt", "name": "booking-receipt", "title": "Booking receipt",
     "description": "Plain-text receipt of one booking.", "mimeType": "text/plain"},
]
PROMPTS = [
    {"name": "draft_cancellation_reply", "title": "Draft a cancellation reply",
     "description": "Draft an email to a traveler who asked to cancel a booking.",
     "arguments": [{"name": "booking_id", "description": "The booking to cancel", "required": True},
                   {"name": "tone", "description": "friendly or formal (default friendly)", "required": False}]},
]


def result(request_id, payload: dict) -> dict:
    payload.setdefault("resultType", "complete")
    payload["_meta"] = {"io.modelcontextprotocol/serverInfo": SERVER_INFO}
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id, code: int, message: str, data: dict | None = None) -> dict:
    body = {"code": code, "message": message}
    if data is not None:
        body["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": body}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def receipt(booking: dict) -> str:
    return (f"Receipt {booking['booking_id']}: {booking['hotel']}, {booking['nights']} nights from "
            f"{booking['check_in']}, {booking['total_eur']:.2f} EUR, {booking['status']}")


# ---- requestState: the server keeps no state between the call and its retry --------------------

def seal_state(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    tag = hmac.new(STATE_KEY, body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{tag}"


def open_state(state: str, expected_call: str) -> dict | None:
    body, _, tag = state.rpartition(".")
    good_tag = hmac.new(STATE_KEY, body.encode(), hashlib.sha256).hexdigest()[:32]
    if not body or not hmac.compare_digest(tag, good_tag):
        return None
    payload = json.loads(base64.urlsafe_b64decode(body))
    if payload["call"] != expected_call or payload["exp"] < time.time():
        return None
    return payload


# ---- tools --------------------------------------------------------------------------------------

def confirm_form(booking: dict) -> dict:
    """Form mode elicitation params: a flat object with primitive fields only."""
    return {"mode": "form",
            "message": f"Cancel {booking['hotel']} from {booking['check_in']} for {booking['traveler']}?",
            "requestedSchema": {"type": "object", "properties": {
                "confirm": {"type": "boolean", "title": "Yes, cancel this booking"},
                "reason": {"type": "string", "title": "Reason",
                           "enum": ["change of plans", "found a better price", "other"]}},
                "required": ["confirm"]}}


def call_tool(request_id, params: dict, capabilities: dict) -> dict:
    name, args = params.get("name"), params.get("arguments", {})
    if name not in {t["name"] for t in TOOLS}:
        return error(request_id, -32602, f"Unknown tool: {name}")
    booking = BOOKINGS.get(args.get("booking_id"))
    if booking is None:  # a tool execution error: the model can read it and fix the argument
        return result(request_id, {"content": [text_block(
            f"No booking with id {args.get('booking_id')!r}. Booking ids look like B-2041.")], "isError": True})

    if name == "get_booking":
        uri = f"bookings://{booking['booking_id']}/receipt"
        return result(request_id, {
            "content": [text_block(json.dumps(booking)),
                        {"type": "resource_link", "uri": uri, "name": "booking-receipt", "mimeType": "text/plain"}],
            "structuredContent": booking, "isError": False})

    # cancel_booking: confirm with the user first
    if "elicitation" not in capabilities:
        return error(request_id, -32021, "Server requires the elicitation capability for this request",
                     {"requiredCapabilities": {"elicitation": {}}})
    call_id = f"tools/call:cancel_booking:{booking['booking_id']}"
    state = params.get("requestState")
    answer = params.get("inputResponses", {}).get("confirm_cancel")
    if state is None or answer is None:
        return result(request_id, {
            "resultType": "input_required",
            "inputRequests": {"confirm_cancel": {"method": "elicitation/create", "params": confirm_form(booking)}},
            "requestState": seal_state({"call": call_id, "exp": int(time.time()) + STATE_TTL_SECONDS})})
    if open_state(state, call_id) is None:
        return error(request_id, -32602, "Invalid or expired requestState")
    if answer.get("action") != "accept" or not answer.get("content", {}).get("confirm"):
        return result(request_id, {"content": [text_block(
            f"The user did not confirm ({answer.get('action')}). Booking {booking['booking_id']} is unchanged.")],
            "isError": False})
    booking["status"] = "cancelled"
    reason = answer["content"].get("reason", "not given")
    return result(request_id, {"content": [text_block(
        f"Booking {booking['booking_id']} is cancelled. Reason: {reason}.")], "isError": False})


# ---- resources ----------------------------------------------------------------------------------

def read_resource(request_id, uri: str) -> dict:
    if uri == "docs://policies/cancellation":
        contents = [{"uri": uri, "mimeType": "text/markdown", "text": POLICY}]
        return result(request_id, {"contents": contents, "ttlMs": 3600000, "cacheScope": "public"})
    match = re.fullmatch(r"bookings://([A-Z]-\d+)/receipt", uri or "")
    if match and match.group(1) in BOOKINGS:
        contents = [{"uri": uri, "mimeType": "text/plain", "text": receipt(BOOKINGS[match.group(1)])}]
        return result(request_id, {"contents": contents, "ttlMs": 60000, "cacheScope": "private"})
    return error(request_id, -32602, "Resource not found", {"uri": uri})


# ---- prompts ------------------------------------------------------------------------------------

def get_prompt(request_id, params: dict) -> dict:
    if params.get("name") != "draft_cancellation_reply":
        return error(request_id, -32602, f"Unknown prompt: {params.get('name')}")
    args = params.get("arguments", {})
    booking = BOOKINGS.get(args.get("booking_id", ""))
    if booking is None:
        return error(request_id, -32602, "Missing or unknown required argument: booking_id")
    tone = args.get("tone", "friendly")
    return result(request_id, {"description": "Cancellation reply", "messages": [
        {"role": "user", "content": text_block(
            f"Write a {tone} email to {booking['traveler']} about cancelling booking {booking['booking_id']} "
            f"({booking['hotel']}, check-in {booking['check_in']}). Apply the policy below and state the fee.")},
        {"role": "user", "content": {"type": "resource", "resource": {
            "uri": "docs://policies/cancellation", "mimeType": "text/markdown", "text": POLICY}}},
    ]})


# ---- dispatch -----------------------------------------------------------------------------------

def handle(message: dict) -> dict:
    request_id, method = message.get("id"), message.get("method")
    params = message.get("params", {})
    meta = params.get("_meta", {})
    version = meta.get("io.modelcontextprotocol/protocolVersion")
    capabilities = meta.get("io.modelcontextprotocol/clientCapabilities")
    if version is None or capabilities is None:
        return error(request_id, -32602, "Missing required _meta fields")
    if version != PROTOCOL_VERSION:
        return error(request_id, -32022, "Unsupported protocol version",
                     {"supported": [PROTOCOL_VERSION], "requested": version})

    if method == "server/discover":
        return result(request_id, {"supportedVersions": [PROTOCOL_VERSION],
                                   "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                                   "instructions": "Travel bookings. Read the cancellation policy before cancelling.",
                                   "ttlMs": 3600000, "cacheScope": "public"})
    if method == "tools/list":
        return result(request_id, {"tools": TOOLS, "ttlMs": 300000, "cacheScope": "public"})
    if method == "tools/call":
        return call_tool(request_id, params, capabilities)
    if method == "resources/list":
        return result(request_id, {"resources": RESOURCES, "ttlMs": 300000, "cacheScope": "public"})
    if method == "resources/templates/list":
        return result(request_id, {"resourceTemplates": TEMPLATES, "ttlMs": 300000, "cacheScope": "public"})
    if method == "resources/read":
        return read_resource(request_id, params.get("uri"))
    if method == "prompts/list":
        return result(request_id, {"prompts": PROMPTS, "ttlMs": 300000, "cacheScope": "public"})
    if method == "prompts/get":
        return get_prompt(request_id, params)
    return error(request_id, -32601, "Method not found")


if __name__ == "__main__":
    for line in sys.stdin:
        if line.strip():
            print(json.dumps(handle(json.loads(line))), flush=True)
