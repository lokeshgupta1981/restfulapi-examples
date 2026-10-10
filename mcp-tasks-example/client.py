"""Calls the invoice-exports MCP server and drives MCP tasks: create, poll, answer, cancel.

The client prints each request and the important fields of each reply.
Run (server on 127.0.0.1:8000): python3 client.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
TASKS_EXT = "io.modelcontextprotocol/tasks"
WITH_TASKS = {"extensions": {TASKS_EXT: {}}, "elicitation": {"form": {}}}
next_id = 0


def send(method: str, params: dict | None = None, capabilities: dict | None = None,
         token: str = "demo-token-alice", show: bool = True) -> dict:
    """POSTs one JSON-RPC request with the 2026-07-28 _meta fields and routing headers."""
    global next_id
    next_id += 1
    params = dict(params or {})
    params["_meta"] = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                       "io.modelcontextprotocol/clientInfo": {"name": "demo-client", "version": "1.0.0"},
                       "io.modelcontextprotocol/clientCapabilities": capabilities or {}}
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "Authorization": f"Bearer {token}", "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": method}
    if method.startswith("tasks/"):
        headers["Mcp-Name"] = params["taskId"]
    elif method == "tools/call":
        headers["Mcp-Name"] = params["name"]
    body = json.dumps({"jsonrpc": "2.0", "id": next_id, "method": method, "params": params}).encode()
    request = urllib.request.Request(URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            status, reply = response.status, json.loads(response.read())
    except urllib.error.HTTPError as failure:
        status, reply = failure.code, json.loads(failure.read())
    if show:
        shown = {k: v for k, v in params.items() if k != "_meta"}
        print(f"--> {method} {json.dumps(shown)}")
        kind = "result" if "result" in reply else "error"
        print(f"<-- HTTP {status} {kind} " + json.dumps(reply.get(kind), indent=2).replace("\n", "\n    "))
        print()
    return reply


def poll(task_id: str, answer_with: dict | None = None) -> dict:
    """Polls tasks/get, honors pollIntervalMs, prints status changes, answers input requests once."""
    last, answered = None, set()
    while True:
        task = send("tasks/get", {"taskId": task_id}, WITH_TASKS, show=False)["result"]
        line = f"{task['status']}: {task.get('statusMessage', '')}"
        if line != last:
            print(f"    tasks/get -> {line}")
            last = line
        if task["status"] in ("completed", "failed", "cancelled"):
            return task
        if task["status"] == "input_required" and answer_with is not None and not answered:
            print("    input_required task: " + json.dumps(task, indent=2).replace("\n", "\n    "))
        if task["status"] == "input_required" and answer_with is not None:
            for key, req in task["inputRequests"].items():
                if key in answered:
                    continue  # the same request can appear in several polls
                print(f"    input request {key!r}: {req['params']['message']}")
                send("tasks/update", {"taskId": task_id, "inputResponses": {key: answer_with}}, WITH_TASKS)
                answered.add(key)
        time.sleep (task.get("pollIntervalMs", 1000) / 1000)


def section(title: str) -> None:
    print("=" * 8, title)


section("1. Discover the server")
send("server/discover")

section("2. A small export finishes inside the tools/call request")
send("tools/call", {"name": "export_invoices", "arguments": {"year": 2026, "month": 9}}, WITH_TASKS)

section("3. A year export needs the tasks extension")
send("tools/call", {"name": "export_invoices", "arguments": {"year": 2025}})

section("4. The server returns a task, the client polls and answers the input request")
created = send("tools/call", {"name": "export_invoices", "arguments": {"year": 2025}}, WITH_TASKS)["result"]
time.sleep (1.0)
send("tasks/get", {"taskId": created["taskId"]}, WITH_TASKS)
final = poll(created["taskId"], answer_with={"action": "accept", "content": {"include": False}})
print("    final task: " + json.dumps(final, indent=2).replace("\n", "\n    "))
print()

section("5. Another user cannot read the task")
send("tasks/get", {"taskId": created["taskId"]}, WITH_TASKS, token="demo-token-bob")

section("6. Cancel a running task")
second = send("tools/call", {"name": "export_invoices", "arguments": {"year": 2024}}, WITH_TASKS, show=False)["result"]
time.sleep (1.0)
send("tasks/cancel", {"taskId": second["taskId"]}, WITH_TASKS)
poll(second["taskId"])
print()

section("7. A JSON-RPC error inside the job ends the task as failed")
third = send("tools/call", {"name": "export_invoices", "arguments": {"year": 2019}}, WITH_TASKS, show=False)["result"]
failed = poll(third["taskId"])
print("    error: " + json.dumps(failed["error"]))
print()

section("8. A tool error is a normal tool result with isError")
send("tools/call", {"name": "export_invoices", "arguments": {"year": 2031}}, WITH_TASKS)

section("9. An unknown task id")
send("tasks/get", {"taskId": "no-such-task"}, WITH_TASKS)
