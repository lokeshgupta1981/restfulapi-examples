"""Streamable HTTP binding: every message is a POST to /mcp.

Run: uvicorn http_server:app --host 127.0.0.1 --port 8000
"""

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from core import PROTOCOL_VERSION, handle

ALLOWED_ORIGINS = {"http://127.0.0.1:8000", "http://localhost:8000"}
app = FastAPI()


def rpc_error(status: int, code: int, message: str, request_id=None) -> JSONResponse:
    body = {"jsonrpc": "2.0", "error": {"code": code, "message": message}}
    if request_id is not None:
        body["id"] = request_id
    return JSONResponse(body, status_code=status)


@app.api_route("/mcp", methods=["GET", "DELETE"])
def old_session_methods():
    # GET streams and DELETE of a session belong to revisions before 2026-07-28.
    return Response(status_code=405, headers={"Allow": "POST"})


@app.post("/mcp")
async def mcp(request: Request):
    origin = request.headers.get("Origin")
    if origin is not None and origin not in ALLOWED_ORIGINS:
        return rpc_error(403, -32600, "origin not allowed")
    message = await request.json()
    params = message.get("params", {})

    # The headers mirror the body so that proxies can route without parsing JSON.
    expected = {"MCP-Protocol-Version": params.get("_meta", {}).get("io.modelcontextprotocol/protocolVersion"),
                "Mcp-Method": message.get("method")}
    if message.get("method") in ("tools/call", "prompts/get", "resources/read"):
        expected["Mcp-Name"] = params.get("name") or params.get("uri")
    for header, value in expected.items():
        if request.headers.get(header) != value:
            return rpc_error(400, -32020, f"Header mismatch: {header}", message.get("id"))

    if "progressToken" in params.get("_meta", {}):
        # The client wants progress, so the reply is an SSE stream scoped to this one request.
        def events():
            for reply in handle(message):
                yield f"event: message\ndata: {json.dumps(reply)}\n\n"
        return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    reply = list(handle(message))[-1]  # a single JSON response
    status = 400 if reply.get("error", {}).get("code") == -32022 else 200
    return JSONResponse(reply, status_code=status)
