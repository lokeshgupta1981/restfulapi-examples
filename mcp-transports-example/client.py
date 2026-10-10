"""Send the same MCP requests over stdio and over Streamable HTTP and print the wire traffic.

  python client.py stdio        starts stdio_server.py as a subprocess
  python client.py http         talks to http_server.py on http://127.0.0.1:8000/mcp
  python client.py http-errors  shows how the HTTP server rejects bad or old-style requests
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

VERSION = "2026-07-28"
URL = "http://127.0.0.1:8000/mcp"


def request(request_id, method, params=None, progress_token=None):
    params = dict(params or {})
    meta = {"io.modelcontextprotocol/protocolVersion": VERSION,
            "io.modelcontextprotocol/clientInfo": {"name": "demo-client", "version": "1.0.0"},
            "io.modelcontextprotocol/clientCapabilities": {}}
    if progress_token:
        meta["progressToken"] = progress_token
    params["_meta"] = meta
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


REQUESTS = [
    request(1, "server/discover"),
    request(2, "tools/list"),
    request(3, "tools/call", {"name": "get_order_status", "arguments": {"order_id": "A-1001"}}),
    request(4, "tools/call", {"name": "export_orders", "arguments": {}}, progress_token="export-1"),
]


def short(message: dict) -> str:
    """Print a message on one line, without the long _meta fields and tool schemas."""
    copy = json.loads(json.dumps(message))
    meta = copy.get("params", {}).pop("_meta", None)
    if meta and "progressToken" in meta:
        copy["params"]["_meta"] = {"progressToken": meta["progressToken"], "...": "..."}
    if "tools" in copy.get("result", {}):
        copy["result"]["tools"] = [tool["name"] for tool in copy["result"]["tools"]]
    return json.dumps(copy)


def run_stdio() -> None:
    start = time.time()
    server = subprocess.Popen([sys.executable, "stdio_server.py"], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for message in REQUESTS:
        server.stdin.write(json.dumps(message) + "\n")  # one message per line
        server.stdin.flush()
        print(f">> {short(message)}")
        while True:
            reply = json.loads(server.stdout.readline())
            print(f"<< [{time.time() - start:4.1f}s] {short(reply)}")
            if reply.get("id") == message["id"]:
                break
    server.stdin.close()  # the shutdown signal for a stdio server
    code = server.wait(timeout=5)
    print(f"server exited with code {code}, stderr: {server.stderr.read().strip().splitlines()}")


def post(message: dict, headers: dict | None = None, method: str = "POST"):
    base = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": VERSION, "Mcp-Method": message["method"]}
    if message["method"] == "tools/call":
        base["Mcp-Name"] = message["params"]["name"]
    base.update(headers or {})
    data = json.dumps(message).encode() if method == "POST" else None
    return urllib.request.urlopen(urllib.request.Request(URL, data=data, headers=base, method=method))


def run_http() -> None:
    start = time.time()
    for message in REQUESTS:
        name = f" Mcp-Name: {message['params']['name']}" if message["method"] == "tools/call" else ""
        print(f">> POST /mcp  Mcp-Method: {message['method']}{name}")
        print(f"   {short(message)}")
        with post(message) as response:
            kind = response.headers["Content-Type"]
            print(f"<< HTTP {response.status} {kind}")
            if kind.startswith("text/event-stream"):
                for line in response:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        print(f"   [{time.time() - start:4.1f}s] data: {short(json.loads(line[6:]))}")
            else:
                print(f"   {short(json.load(response))}")


def show_error(label: str, call) -> None:
    print(f"== {label}")
    try:
        with call() as response:
            print(f"<< HTTP {response.status}, Mcp-Session-Id in response: {'Mcp-Session-Id' in response.headers}")
            print(f"   {short(json.load(response))}")
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        allow = f", Allow: {error.headers['Allow']}" if error.headers.get("Allow") else ""
        print(f"<< HTTP {error.code}{allow}")
        if body:
            print(f"   {body}")


def run_http_errors() -> None:
    call = request(5, "tools/call", {"name": "get_order_status", "arguments": {"order_id": "A-1002"}})
    show_error("Mcp-Name header says one tool, the body calls another",
               lambda: post(call, {"Mcp-Name": "export_orders"}))
    old = request(6, "tools/list")
    old["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2025-11-25"
    show_error("Request for protocol version 2025-11-25", lambda: post(old, {"MCP-Protocol-Version": "2025-11-25"}))
    show_error("GET /mcp, the old standalone SSE stream", lambda: post(request(7, "tools/list"), method="GET"))
    show_error("An old client sends Mcp-Session-Id", lambda: post(request(8, "tools/list"), {"Mcp-Session-Id": "abc"}))


{"stdio": run_stdio, "http": run_http, "http-errors": run_http_errors}[sys.argv[1]]()
