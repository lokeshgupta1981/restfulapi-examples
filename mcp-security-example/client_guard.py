"""Client-side checks from the article.

  pin    store a SHA-256 hash of every tool definition after the user approves the tools
  check  compare the current tool definitions with the pinned hashes and scan the
         descriptions for instructions aimed at the model
  call   call one tool and print the HTTP status, the WWW-Authenticate header and the result

Examples:
  python client_guard.py pin --token "$ALICE"
  python client_guard.py check --token "$ALICE"
  python client_guard.py call add_item '{"cart_id": "...", "sku": "SKU-1"}' --token "$ALICE"
"""

import argparse
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

SERVER = "http://127.0.0.1:8000/mcp"
LOCK_FILE = pathlib.Path(__file__).with_name("tools.lock.json")
PROTOCOL_VERSION = "2026-07-28"

# Text that a tool description has no reason to contain. The list catches known
# patterns only, so it supports the hash pin and the user's review, it does not replace them.
SUSPICIOUS = [
    r"<important>", r"ignore (all|previous|the above)", r"do not (tell|mention|inform)",
    r"\.ssh", r"id_rsa", r"\.env\b", r"mcp\.json", r"password", r"send .* to http",
]


def post(message: dict, token: str, origin: str | None = None) -> tuple[int, dict, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": message["method"],
        "Authorization": f"Bearer {token}",
    }
    if message["method"] == "tools/call":
        headers["Mcp-Name"] = message["params"]["name"]
    if origin:
        headers["Origin"] = origin
    message["params"].setdefault("_meta", {})["io.modelcontextprotocol/protocolVersion"] = PROTOCOL_VERSION
    request = urllib.request.Request(SERVER, data=json.dumps(message).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response), ""
    except urllib.error.HTTPError as error:
        return error.code, json.load(error), error.headers.get("WWW-Authenticate", "")


def tool_hash(tool: dict) -> str:
    """Hash the whole definition: name, description, schemas and annotations."""
    canonical = json.dumps(tool, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def list_tools(token: str) -> list[dict]:
    status, body, _ = post({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, token)
    if status != 200:
        sys.exit(f"tools/list failed with HTTP {status}: {body}")
    return body["result"]["tools"]


def pin(token: str) -> None:
    hashes = {tool["name"]: tool_hash(tool) for tool in list_tools(token)}
    LOCK_FILE.write_text(json.dumps(hashes, indent=2) + "\n")
    for name, digest in hashes.items():
        print(f"pinned {name} sha256:{digest[:12]}")


def check(token: str) -> int:
    pinned = json.loads(LOCK_FILE.read_text())
    problems = 0
    for tool in list_tools(token):
        name = tool["name"]
        digest = tool_hash(tool)
        if name not in pinned:
            print(f"NEW      {name}: not approved yet, ask the user before exposing it to the model")
            problems += 1
        elif pinned[name] != digest:
            print(f"CHANGED  {name}: sha256:{pinned[name][:12]} -> sha256:{digest[:12]}, disable until re-approved")
            problems += 1
        else:
            print(f"OK       {name}")
        for pattern in SUSPICIOUS:
            match = re.search(pattern, tool.get("description", ""), re.IGNORECASE)
            if match:
                print(f"SUSPECT  {name}: description contains {match.group(0)!r}")
                problems += 1
    return 1 if problems else 0


def call(name: str, arguments: str, token: str, origin: str | None) -> None:
    message = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
               "params": {"name": name, "arguments": json.loads(arguments)}}
    status, body, challenge = post(message, token, origin)
    print(f"HTTP {status}")
    if challenge:
        print(f"WWW-Authenticate: {challenge}")
    if "result" in body:
        result = body["result"]
        print(f"isError={result['isError']} text={result['content'][0]['text']}")
    else:
        print(f"error: {body['error']['message']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["pin", "check", "call"])
    parser.add_argument("tool", nargs="?")
    parser.add_argument("arguments", nargs="?", default="{}")
    parser.add_argument("--token", required=True)
    parser.add_argument("--origin")
    options = parser.parse_args()
    if options.command == "pin":
        pin(options.token)
    elif options.command == "check":
        sys.exit(check(options.token))
    else:
        call(options.tool, options.arguments, options.token, options.origin)
