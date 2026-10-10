"""Calls the Expense Policy Agent with plain HTTP and prints the A2A 1.0 wire format."""

import json
import urllib.request
import uuid

BASE = "http://127.0.0.1:9999"


def show(label: str, value) -> None:
    print(f"\n== {label}\n{json.dumps(value, indent=2)}")


def rpc(method: str, params: dict, version: str | None = "1.0") -> dict:
    headers = {"Content-Type": "application/json"}
    if version:
        headers["A2A-Version"] = version
    body = {"jsonrpc": "2.0", "id": str(uuid.uuid4())[:8], "method": method, "params": params}
    request = urllib.request.Request(f"{BASE}/a2a", data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def user_message(text: str, **ids) -> dict:
    return {"message": {"messageId": f"msg-{uuid.uuid4().hex[:8]}", "role": "ROLE_USER", "parts": [{"text": text}],
                        **ids}}


# 1. Discovery
with urllib.request.urlopen(f"{BASE}/.well-known/agent-card.json") as response:
    card = json.load(response)
print("Agent Card:", card["name"], "| skills:", [s["id"] for s in card["skills"]],
      "| interface:", card["supportedInterfaces"][0])

# 2. A request without A2A-Version is treated as version 0.3
show("SendMessage without A2A-Version", rpc("SendMessage", user_message("Check expense: hotel 180 EUR"), None))

# 3. A check that needs more input
first = rpc("SendMessage", user_message("Check expense: hotel 180 EUR"))
task = first["result"]["task"]
print("\n== SendMessage, missing receipt")
print("state:", task["status"]["state"], "| agent says:", task["status"]["message"]["parts"][0]["text"])

# 4. The follow-up message continues the same task
second = rpc("SendMessage", user_message("Receipt R-5512", taskId=task["id"], contextId=task["contextId"]))
show("SendMessage, follow-up with taskId", second)

# 5. Read the task later, and try to cancel a finished task
done = rpc("GetTask", {"id": task["id"], "historyLength": 1})
print("\n== GetTask:", done["result"]["status"]["state"], "| history items:", len(done["result"]["history"]))
show("CancelTask on a completed task", rpc("CancelTask", {"id": task["id"]}))

# 6. Streaming over server-sent events
body = {"jsonrpc": "2.0", "id": "s1", "method": "SendStreamingMessage", "params": user_message("Audit expenses for October")}
request = urllib.request.Request(f"{BASE}/a2a", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "A2A-Version": "1.0"})
print("\n== SendStreamingMessage (one line per SSE event)")
with urllib.request.urlopen(request) as response:
    print("Content-Type:", response.headers["Content-Type"])
    for raw in response:
        line = raw.decode().strip()
        if line.startswith("data: "):
            result = json.loads(line[6:])["result"]
            kind = next(iter(result))
            detail = (result[kind]["status"]["state"] if kind in ("task", "statusUpdate")
                      else result[kind]["artifact"]["parts"][0]["text"])
            print(f"{kind:<15} {detail}")
