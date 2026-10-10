"""Two small gateways in one app on http://127.0.0.1:8000.

AI gateway   POST /v1/chat/completions  (OpenAI-compatible)
  - virtual keys per team, model aliases, token budget per minute (HTTP 429 + Retry-After)
  - fallback to the next provider when a provider fails, usage and cost log
MCP gateway  POST /mcp  (Streamable HTTP, protocol 2026-07-28)
  - one endpoint for two MCP servers, tool names prefixed with the server name
  - per-team tool policy on tools/list and tools/call, audit log
  - calls the MCP servers with its own service token, never with the client's token

Run: uvicorn gateway:app --host 127.0.0.1 --port 8000   (backends on port 9001)
"""

import json
import time
import urllib.error
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

BACKEND = "http://127.0.0.1:9001"
SERVICE_TOKEN = "svc-gateway-demo-token"  # the gateway's own credential for the MCP servers
LOG = open("gateway.log", "a", buffering=1)

app = FastAPI()


def log(event: dict) -> None:
    LOG.write(json.dumps(event) + "\n")


def post_json(url: str, body: dict, headers: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


# ---------------------------------------------------------------- AI gateway

VIRTUAL_KEYS = {  # demo keys, a real gateway stores hashed keys in a database
    "vk-support-123": {"team": "support", "models": {"fast"}, "tokens_per_minute": 40},
    "vk-analytics-456": {"team": "analytics", "models": {"fast", "smart"}, "tokens_per_minute": 2000},
}
ROUTES = {  # alias -> providers in order of preference
    "fast": [("alpha", "alpha-mini"), ("beta", "beta-small")],
    "smart": [("beta", "beta-large")],
}
PRICE_PER_1K_TOKENS = {"alpha-mini": 0.0004, "beta-small": 0.0006, "beta-large": 0.0050}  # example prices
USAGE: dict[str, tuple[int, int]] = {}  # key -> (window start minute, tokens used)


def openai_error(status: int, message: str, error_type: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": error_type}}, status_code=status, headers=headers)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    key = request.headers.get("Authorization", "").removeprefix("Bearer ")
    account = VIRTUAL_KEYS.get(key)
    if account is None:
        return openai_error(401, "invalid virtual key", "invalid_request_error")
    body = await request.json()
    alias = body.get("model")
    if alias not in account["models"]:
        return openai_error(403, f"team {account['team']} may not use model {alias}", "permission_error")

    # Token budget per minute: estimate the prompt now, count the real usage after the call.
    now = time.time()
    minute = int(now // 60)
    start, used = USAGE.get(key, (minute, 0))
    if start != minute:
        start, used = minute, 0
    estimate = sum(len(m["content"]) for m in body["messages"]) // 4 + 1
    if used + estimate > account["tokens_per_minute"]:
        retry_after = 60 - int(now % 60)
        log({"gateway": "ai", "team": account["team"], "model": alias, "result": "429", "used": used})
        return openai_error(429, "token budget for this minute is used up", "rate_limit_error",
                            {"Retry-After": str(retry_after)})

    for provider, model in ROUTES[alias]:
        status, reply = post_json(f"{BACKEND}/{provider}/v1/chat/completions", {**body, "model": model},
                                  {"Authorization": f"Bearer provider-key-for-{provider}"})
        if status >= 500:
            log({"gateway": "ai", "team": account["team"], "model": alias, "provider": provider,
                 "result": f"{status}, trying next provider"})
            continue
        tokens = reply["usage"]["total_tokens"]
        USAGE[key] = (start, used + tokens)
        cost = f"{tokens / 1000 * PRICE_PER_1K_TOKENS[model]:.6f}"
        log({"gateway": "ai", "team": account["team"], "model": alias, "provider": provider,
             "tokens": tokens, "cost_usd": cost})
        return JSONResponse(reply, headers={"X-Gateway-Provider": provider})
    return openai_error(502, "all providers failed", "api_error")


# ---------------------------------------------------------------- MCP gateway

MCP_SERVERS = {"crm": f"{BACKEND}/crm/mcp", "tickets": f"{BACKEND}/tickets/mcp"}
CLIENT_TOKENS = {  # demo tokens, a real gateway validates OAuth tokens issued for the gateway
    "mcp-support-token": "support",
    "mcp-admin-token": "admin",
}
POLICY = {  # team -> tools it may see and call, "*" means every tool
    "support": {"crm__search_customers", "tickets__get_ticket"},
    "admin": {"*"},
}


def allowed(team: str, tool: str) -> bool:
    return "*" in POLICY[team] or tool in POLICY[team]


def backend_call(server: str, method: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {SERVICE_TOKEN}", "MCP-Protocol-Version": "2026-07-28",
               "Mcp-Method": method, "Accept": "application/json, text/event-stream"}
    if method == "tools/call":
        headers["Mcp-Name"] = params["name"]
    _, reply = post_json(MCP_SERVERS[server], {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                         headers)
    return reply["result"]


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    team = CLIENT_TOKENS.get(request.headers.get("Authorization", "").removeprefix("Bearer "))
    if team is None:
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32600, "message": "invalid token"}},
                            status_code=401, headers={"WWW-Authenticate": "Bearer"})
    message = await request.json()
    request_id, method, params = message.get("id"), message["method"], message.get("params", {})

    if method == "tools/list":
        tools = []
        for server in MCP_SERVERS:
            for tool in backend_call(server, "tools/list", {})["tools"]:
                name = f"{server}__{tool['name']}"
                if allowed(team, name):
                    tools.append({**tool, "name": name})
        # The list depends on the caller, so shared caches must not reuse it.
        result = {"resultType": "complete", "tools": tools, "ttlMs": 60000, "cacheScope": "private"}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    if method == "tools/call":
        name = params.get("name", "")
        if request.headers.get("Mcp-Name") != name:
            return JSONResponse({"jsonrpc": "2.0", "id": request_id,
                                 "error": {"code": -32020, "message": "Mcp-Name header does not match the body"}},
                                status_code=400)
        server, _, tool = name.partition("__")
        known = server in MCP_SERVERS and tool in {t["name"] for t in backend_call(server, "tools/list", {})["tools"]}
        if not known or not allowed(team, name):
            log({"gateway": "mcp", "team": team, "tool": name, "result": "denied"})
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        result = backend_call(server, "tools/call", {"name": tool, "arguments": params.get("arguments", {})})
        log({"gateway": "mcp", "team": team, "tool": name, "arguments": params.get("arguments", {}),
             "result": "ok"})
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}},
                        status_code=404)
