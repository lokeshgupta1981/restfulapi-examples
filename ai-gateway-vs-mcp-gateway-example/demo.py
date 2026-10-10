"""Send one request to a gateway and print the parts that matter.

  python demo.py chat KEY MODEL "prompt"
  python demo.py tools TOKEN
  python demo.py call TOKEN TOOL '{"arg": "value"}'
"""

import json
import sys
import urllib.error
import urllib.request

GATEWAY = "http://127.0.0.1:8000"


def send(path: str, body: dict, headers: dict) -> tuple[int, dict, dict]:
    request = urllib.request.Request(GATEWAY + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, dict(response.headers), json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), json.load(error)


def mcp_headers(token: str, method: str, name: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}", "MCP-Protocol-Version": "2026-07-28",
               "Mcp-Method": method, "Accept": "application/json, text/event-stream"}
    if name:
        headers["Mcp-Name"] = name
    return headers


command = sys.argv[1]
if command == "chat":
    key, model, prompt = sys.argv[2:5]
    status, headers, body = send("/v1/chat/completions",
                                 {"model": model, "messages": [{"role": "user", "content": prompt}]},
                                 {"Authorization": f"Bearer {key}"})
    print(f"HTTP {status}")
    for name in ("X-Gateway-Provider", "Retry-After"):
        if name.lower() in {h.lower() for h in headers}:
            print(f"{name}: {next(v for h, v in headers.items() if h.lower() == name.lower())}")
    if status == 200:
        print(f"answer: {body['choices'][0]['message']['content']}")
        print(f"usage: {body['usage']}")
    else:
        print(f"error: {body['error']}")
elif command == "tools":
    status, _, body = send("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                           mcp_headers(sys.argv[2], "tools/list"))
    print(f"HTTP {status}")
    result = body["result"]
    print("tools: " + ", ".join(tool["name"] for tool in result["tools"]))
    print(f"cacheScope: {result['cacheScope']}")
elif command == "call":
    token, tool, arguments = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
    message = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    status, _, body = send("/mcp", message, mcp_headers(token, "tools/call", tool))
    print(f"HTTP {status}")
    print(json.dumps(body.get("result") or body.get("error")))
