"""Starts server.py over stdio and uses every primitive the way a host app would.

The client prints each request and the reply. It hides the serverInfo entry in result._meta,
which every reply carries, so the output stays short.
Run: python3 client.py
"""

import json
import subprocess
import sys

PROTOCOL_VERSION = "2026-07-28"
CLIENT_INFO = {"name": "demo-host", "version": "1.0.0"}

server = subprocess.Popen([sys.executable, "server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
next_id = 0


def send(method: str, params: dict | None = None, capabilities: dict | None = None, show: bool = True) -> dict:
    """Sends one request. Every request carries its protocol version and client capabilities in _meta."""
    global next_id
    next_id += 1
    params = dict(params or {})
    params["_meta"] = {"io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
                       "io.modelcontextprotocol/clientInfo": CLIENT_INFO,
                       "io.modelcontextprotocol/clientCapabilities": capabilities or {}}
    request = {"jsonrpc": "2.0", "id": next_id, "method": method, "params": params}
    server.stdin.write(json.dumps(request) + "\n")
    server.stdin.flush()
    reply = json.loads(server.stdout.readline())
    if show:
        shown = {k: v for k, v in params.items() if k != "_meta"}
        print(f"--> {method} {json.dumps(shown) if shown else ''}".rstrip())
        print_reply(reply)
    return reply


def print_reply(reply: dict) -> None:
    body = dict(reply.get("result") or {})
    body.pop("_meta", None)
    if "error" in reply:
        body = {"error": reply["error"]}
    print("<-- " + json.dumps(body, indent=2).replace("\n", "\n    ") + "\n")


def section(title: str) -> None:
    print("=" * 8, title)


section("1. Discover the server")
send("server/discover")

section("2. Tools: the model picks and calls them")
tools = send("tools/list", show=False)["result"]["tools"]
for tool in tools:
    print(f"tool {tool['name']}: outputSchema={'outputSchema' in tool}, annotations={tool['annotations']}")
print()
booking = send("tools/call", {"name": "get_booking", "arguments": {"booking_id": "B-2041"}})
link = next(block for block in booking["result"]["content"] if block["type"] == "resource_link")
send("resources/read", {"uri": link["uri"]})
send("tools/call", {"name": "get_booking", "arguments": {"booking_id": "B-9999"}})
send("tools/call", {"name": "book_flight", "arguments": {}})

section("3. Resources: the host app picks what to read")
for item in send("resources/list", show=False)["result"]["resources"]:
    print(f"resource {item['uri']} ({item['mimeType']})")
for item in send("resources/templates/list", show=False)["result"]["resourceTemplates"]:
    print(f"template {item['uriTemplate']} ({item['mimeType']})")
print()
send("resources/read", {"uri": "docs://policies/cancellation"})
send("resources/read", {"uri": "bookings://B-7777/receipt"})

section("4. Prompts: the user picks them, for example as /draft_cancellation_reply")
for item in send("prompts/list", show=False)["result"]["prompts"]:
    print(f"prompt {item['name']} args={[a['name'] for a in item['arguments']]}")
print()
send("prompts/get", {"name": "draft_cancellation_reply", "arguments": {"booking_id": "B-2042", "tone": "formal"}})
send("prompts/get", {"name": "draft_cancellation_reply", "arguments": {}})

section("5. Elicitation inside a tool call (multi round-trip request)")
cancel = {"name": "cancel_booking", "arguments": {"booking_id": "B-2042"}}
send("tools/call", cancel)  # no elicitation capability declared
form_client = {"elicitation": {"form": {}}}
first = send("tools/call", cancel, capabilities=form_client)
state = first["result"]["requestState"]
tampered = state[:-4] + ("0000" if not state.endswith("0000") else "1111")
answer = {"confirm_cancel": {"action": "accept", "content": {"confirm": True, "reason": "change of plans"}}}
send("tools/call", {**cancel, "inputResponses": answer, "requestState": tampered}, capabilities=form_client)
send("tools/call", {**cancel, "inputResponses": answer, "requestState": state}, capabilities=form_client)
final = send("tools/call", {"name": "get_booking", "arguments": {"booking_id": "B-2042"}}, show=False)
print("status of B-2042 after the retry:", final["result"]["structuredContent"]["status"])

server.stdin.close()
server.wait()
