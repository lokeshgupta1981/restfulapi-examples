"""An A2A 1.0 agent server, written at the wire level with FastAPI (JSON-RPC binding).

GET  /.well-known/agent-card.json   the Agent Card
POST /a2a                           JSON-RPC 2.0: SendMessage, SendStreamingMessage, GetTask, CancelTask

The "Expense Policy Agent" of a finance team checks travel expenses for other agents.
  - "check" requests finish at once, or stop in TASK_STATE_INPUT_REQUIRED when the receipt is missing
  - "audit" requests stream progress over server-sent events
The agent logic is a few fixed rules, so the output is predictable. A real agent would call a model
and use tools (for example through MCP) inside handle().

Run: uvicorn expense_agent:app --host 127.0.0.1 --port 9999
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

BASE_URL = "http://127.0.0.1:9999"
LIMITS_EUR = {"hotel": 200, "meal": 60, "taxi": 80}
app = FastAPI()
tasks: dict[str, dict] = {}  # task id -> Task object (in memory)

AGENT_CARD = {
    "name": "Expense Policy Agent",
    "description": "Checks travel expenses against the company travel policy and audits monthly expense reports.",
    "supportedInterfaces": [{"url": f"{BASE_URL}/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
    "provider": {"organization": "Example Corp Finance", "url": "https://finance.example.com"},
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["application/json", "text/plain"],
    "skills": [
        {"id": "check-expense", "name": "Check an expense",
         "description": "Checks one expense against the policy limit. Needs the receipt id.",
         "tags": ["expenses", "policy"], "examples": ["Check expense: hotel 180 EUR, receipt R-5512"]},
        {"id": "audit-report", "name": "Audit a monthly report",
         "description": "Audits all expenses of a month and streams progress.",
         "tags": ["expenses", "audit"], "examples": ["Audit expenses for October"]},
    ],
}

ERRORS = {  # A2A error type -> (JSON-RPC code, message), from the A2A specification section 5.4
    "TaskNotFoundError": (-32001, "Task not found"),
    "TaskNotCancelableError": (-32002, "Task cannot be canceled"),
    "VersionNotSupportedError": (-32009, "Protocol version not supported"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def agent_message(text: str, context_id: str, task_id: str) -> dict:
    return {"messageId": new_id("msg"), "contextId": context_id, "taskId": task_id, "role": "ROLE_AGENT",
            "parts": [{"text": text}]}


def rpc_result(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id, error_type: str, reason_data: dict | None = None) -> JSONResponse:
    code, message = ERRORS[error_type]
    error = {"code": code, "message": message}
    if reason_data:
        error["data"] = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "domain": "a2a-protocol.org",
                          **reason_data}]
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": error})


@app.get("/.well-known/agent-card.json")
async def agent_card():
    return JSONResponse(AGENT_CARD, headers={"Cache-Control": "max-age=3600", "ETag": '"1.0.0"'})


def text_of(message: dict) -> str:
    return " ".join(part.get("text", "") for part in message.get("parts", []))


def check_expense(task: dict, message: dict) -> None:
    """Moves the task to COMPLETED with an artifact, or to INPUT_REQUIRED when the receipt is missing."""
    history_text = " ".join(text_of(m) for m in task["history"] if m["role"] == "ROLE_USER")
    category = next((c for c in LIMITS_EUR if c in history_text.lower()), None)
    amount = re.search(r"(\d+)\s*EUR", history_text)
    receipt = re.search(r"R-\d+", history_text)
    if receipt is None:
        task["status"] = {"state": "TASK_STATE_INPUT_REQUIRED", "timestamp": now(),
                          "message": agent_message("Please send the receipt id (for example R-1234).",
                                                   task["contextId"], task["id"])}
        return
    approved = int(amount.group(1)) <= LIMITS_EUR[category]
    task["artifacts"] = [{"artifactId": new_id("art"), "name": "policy-check", "parts": [
        {"data": {"category": category, "amountEur": int(amount.group(1)), "limitEur": LIMITS_EUR[category],
                  "receipt": receipt.group(0), "approved": approved}, "mediaType": "application/json"},
        {"text": f"{category} {amount.group(1)} EUR is {'within' if approved else 'over'} the "
                 f"{LIMITS_EUR[category]} EUR limit."}]}]
    task["status"] = {"state": "TASK_STATE_COMPLETED", "timestamp": now()}


def start_or_continue(params: dict) -> dict:
    message = params["message"]
    task_id = message.get("taskId")
    if task_id:  # a follow-up message for a task in TASK_STATE_INPUT_REQUIRED
        task = tasks[task_id]
    else:
        context_id = message.get("contextId") or new_id("ctx")
        task = {"id": new_id("task"), "contextId": context_id,
                "status": {"state": "TASK_STATE_SUBMITTED", "timestamp": now()}, "artifacts": [], "history": []}
        tasks[task["id"]] = task
    task["history"].append({**message, "taskId": task["id"], "contextId": task["contextId"]})
    return task


@app.post("/a2a")
async def a2a(request: Request):
    body = await request.json()
    request_id, method, params = body.get("id"), body.get("method"), body.get("params", {})
    version = request.headers.get("A2A-Version") or "0.3"  # a missing or empty header means 0.3 (spec 3.6.2)
    if version != "1.0":
        return rpc_error(request_id, "VersionNotSupportedError",
                         {"reason": "VERSION_NOT_SUPPORTED", "metadata": {"requested": version, "supported": "1.0"}})

    if method == "SendMessage":
        if params["message"].get("taskId") and params["message"]["taskId"] not in tasks:
            return rpc_error(request_id, "TaskNotFoundError", {"reason": "TASK_NOT_FOUND"})
        task = start_or_continue(params)
        check_expense(task, params["message"])
        return rpc_result(request_id, {"task": task})

    if method == "SendStreamingMessage":
        task = start_or_continue(params)
        return StreamingResponse(audit_stream(request_id, task), media_type="text/event-stream")

    if method == "GetTask":
        task = tasks.get(params.get("id"))
        if task is None:
            return rpc_error(request_id, "TaskNotFoundError",
                             {"reason": "TASK_NOT_FOUND", "metadata": {"taskId": str(params.get("id"))}})
        keep = params.get("historyLength")
        return rpc_result(request_id, {**task, "history": task["history"][-keep:] if keep else task["history"]})

    if method == "CancelTask":
        task = tasks.get(params.get("id"))
        if task is None:
            return rpc_error(request_id, "TaskNotFoundError", {"reason": "TASK_NOT_FOUND"})
        if task["status"]["state"] in ("TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED",
                                       "TASK_STATE_REJECTED"):
            return rpc_error(request_id, "TaskNotCancelableError",
                             {"reason": "TASK_NOT_CANCELABLE", "metadata": {"state": task["status"]["state"]}})
        task["status"] = {"state": "TASK_STATE_CANCELED", "timestamp": now()}
        return rpc_result(request_id, task)

    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}})


async def audit_stream(request_id, task: dict):
    def event(payload: dict) -> str:
        return f"data: {json.dumps(rpc_result(request_id, payload))}\n\n"

    task["status"] = {"state": "TASK_STATE_WORKING", "timestamp": now()}
    yield event({"task": task})
    artifact_id = new_id("art")
    findings = ["12 expenses checked.", "1 hotel night over the limit (240 EUR).", "Total 1,830 EUR."]
    for i, line in enumerate(findings):
        await asyncio.sleep (0.2)  # stands in for real work
        yield event({"artifactUpdate": {"taskId": task["id"], "contextId": task["contextId"],
                                        "artifact": {"artifactId": artifact_id, "name": "audit-report",
                                                     "parts": [{"text": line}]},
                                        "append": i > 0, "lastChunk": i == len(findings) - 1}})
    task["artifacts"] = [{"artifactId": artifact_id, "name": "audit-report", "parts": [{"text": " ".join(findings)}]}]
    task["status"] = {"state": "TASK_STATE_COMPLETED", "timestamp": now()}
    yield event({"statusUpdate": {"taskId": task["id"], "contextId": task["contextId"], "status": task["status"]}})
