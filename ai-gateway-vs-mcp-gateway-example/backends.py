"""Stand-ins for the services behind the gateways, on http://127.0.0.1:9001.

- Two LLM providers with an OpenAI-compatible POST /<provider>/v1/chat/completions.
  The provider "alpha" returns HTTP 503 while the file alpha_down.flag exists.
- Two MCP servers (Streamable HTTP, protocol 2026-07-28): /crm/mcp and /tickets/mcp.
  Both accept only the gateway's own service token, never a client token.

Run: uvicorn backends:app --host 127.0.0.1 --port 9001
"""

import pathlib

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

GATEWAY_SERVICE_TOKEN = "svc-gateway-demo-token"  # demo value, the backends trust only the gateway
DOWN_FLAG = pathlib.Path(__file__).with_name("alpha_down.flag")

app = FastAPI()


@app.post("/{provider}/v1/chat/completions")
async def chat(provider: str, request: Request):
    if provider == "alpha" and DOWN_FLAG.exists():
        return JSONResponse({"error": {"message": "alpha is overloaded", "type": "server_error"}}, status_code=503)
    body = await request.json()
    prompt = body["messages"][-1]["content"]
    answer = f"[{provider}/{body['model']}] Summary: {prompt[:40]}"
    prompt_tokens = len(prompt) // 4 + 1
    completion_tokens = len(answer) // 4 + 1
    return {
        "id": f"chatcmpl-{provider}-1", "object": "chat.completion", "model": body["model"],
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                  "total_tokens": prompt_tokens + completion_tokens},
    }


SERVERS = {
    "crm": [
        {"name": "search_customers", "description": "Find customers by name.",
         "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        {"name": "delete_customer", "description": "Delete a customer record.",
         "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
         "annotations": {"destructiveHint": True}},
    ],
    "tickets": [
        {"name": "get_ticket", "description": "Read one support ticket.",
         "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    ],
}


@app.post("/{server}/mcp")
async def mcp(server: str, request: Request):
    if request.headers.get("Authorization") != f"Bearer {GATEWAY_SERVICE_TOKEN}":
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32600, "message": "unknown token"}}, status_code=401)
    message = await request.json()
    if message["method"] == "tools/list":
        result = {"tools": SERVERS[server], "ttlMs": 60000, "cacheScope": "public"}
    else:
        name = message["params"]["name"]
        args = message["params"].get("arguments", {})
        result = {"content": [{"type": "text", "text": f"{server}.{name} ran with {args}"}], "isError": False}
    return {"jsonrpc": "2.0", "id": message["id"], "result": {"resultType": "complete", **result}}
