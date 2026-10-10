"""An MCP server with the Tasks extension (io.modelcontextprotocol/tasks) for a long tool call.

Protocol 2026-07-28 over Streamable HTTP: every message is a POST to /mcp with a JSON response.

The tool export_invoices exports the invoices of an accounting app.
  - One month is small, so the server answers the tools/call request with the normal result.
  - A whole year takes several seconds, so the server returns a task (resultType "task") and the
    client polls tasks/get. Halfway through, the task asks the user whether customer emails may be
    included (status input_required), and the client answers with tasks/update.
  - Year 2019 is in an archive that is offline in this demo, so its task ends as "failed".

Each task belongs to the user who created it (from the bearer token), and task ids are random.
Run: uvicorn server:app --host 127.0.0.1 --port 8000
"""

import asyncio
import secrets
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PROTOCOL_VERSION = "2026-07-28"
TASKS_EXT = "io.modelcontextprotocol/tasks"
SERVER_INFO = {"name": "invoice-exports", "version": "1.0.0"}
USERS = {"demo-token-alice": "alice", "demo-token-bob": "bob"}  # demo bearer tokens, not real secrets
STEP_SECONDS = 0.4  # time to export one month (stands in for real work)
TASK_TTL_MS = 600_000
POLL_INTERVAL_MS = 1_000

app = FastAPI()
tasks: dict[str, dict] = {}  # task id -> task record (a real server stores tasks in a database)

EXPORT_TOOL = {
    "name": "export_invoices",
    "title": "Export invoices",
    "description": "Export the invoices of one month (fast) or a whole year (runs as a task) to a CSV file.",
    "inputSchema": {"type": "object", "properties": {
        "year": {"type": "integer", "minimum": 2015},
        "month": {"type": "integer", "minimum": 1, "maximum": 12}},
        "required": ["year"], "additionalProperties": False},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def result(request_id, payload: dict) -> dict:
    payload.setdefault("resultType", "complete")
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id, code: int, message: str, data: dict | None = None) -> dict:
    body = {"code": code, "message": message}
    if data is not None:
        body["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": body}


def export_result(year: int, month: int | None, rows: int, with_emails: bool) -> dict:
    period = f"{year}-{month:02d}" if month else str(year)
    file = f"invoices-{period}.csv"
    data = {"file": file, "rows": rows, "customerEmails": with_emails}
    return {"content": [{"type": "text", "text": f"Exported {rows} invoices to {file}."}],
            "structuredContent": data, "isError": False}


def public_view(task: dict) -> dict:
    """The task as tasks/get returns it: the common fields plus the fields of its status."""
    view = {k: task[k] for k in ("taskId", "status", "createdAt", "lastUpdatedAt", "ttlMs", "pollIntervalMs")}
    if task.get("statusMessage"):
        view["statusMessage"] = task["statusMessage"]
    if task["status"] == "input_required":
        view["inputRequests"] = task["inputRequests"]
    if task["status"] == "completed":
        view["result"] = task["result"]
    if task["status"] == "failed":
        view["error"] = task["error"]
    return view


def set_status(task: dict, status: str, message: str | None = None) -> None:
    task["status"], task["lastUpdatedAt"] = status, now()
    if message is not None:
        task["statusMessage"] = message


async def run_year_export(task: dict, year: int, can_elicit: bool) -> None:
    """Background job behind one task. It checks the cancel flag between steps (cooperative cancel)."""
    with_emails = False
    for month in range(1, 13):
        if task["cancelRequested"]:
            set_status(task, "cancelled", f"Cancelled after {month - 1} of 12 months.")
            return
        if year == 2019 and month == 4:
            task["error"] = {"code": -32603, "message": "Archive storage for 2019 is unavailable"}
            set_status(task, "failed", "Export stopped at 2019-04, the archive did not respond.")
            return
        if month == 7 and can_elicit:  # ask the user once, only if the client declared elicitation
            task["inputRequests"] = {"include_emails": {"method": "elicitation/create", "params": {
                "mode": "form",
                "message": f"The {year} export has reached July. Include customer email addresses in the file?",
                "requestedSchema": {"type": "object", "properties": {
                    "include": {"type": "boolean", "title": "Include customer emails"}},
                    "required": ["include"]}}}}
            set_status(task, "input_required", "Waiting for the user to decide about customer emails.")
            while "include_emails" not in task["answers"] and not task["cancelRequested"]:
                await asyncio.sleep (0.1)
            if task["cancelRequested"]:
                continue  # the check at the top of the loop ends the job
            answer = task["answers"]["include_emails"]
            with_emails = answer.get("action") == "accept" and bool(answer.get("content", {}).get("include"))
            task.pop("inputRequests", None)
        set_status(task, "working", f"Exported {month - 1} of 12 months.")
        await asyncio.sleep (STEP_SECONDS)
    task["result"] = export_result(year, None, 14_208, with_emails)
    set_status(task, "completed", "Exported 12 of 12 months.")


def find_task(request_id, params: dict, user: str):
    task = tasks.get(params.get("taskId", ""))
    if task is None or task["owner"] != user:  # another user's task looks like an unknown task
        return None, error(request_id, -32602, "Failed to retrieve task: Task not found")
    return task, None


def call_tool(request_id, params: dict, capabilities: dict, user: str) -> dict:
    if params.get("name") != "export_invoices":
        return error(request_id, -32602, f"Unknown tool: {params.get('name')}")
    args = params.get("arguments", {})
    year, month = args.get("year"), args.get("month")
    if not isinstance(year, int) or year > datetime.now().year:
        return result(request_id, {"content": [{"type": "text", "text": f"No invoices exist for year {year}."}],
                                   "isError": True})
    if month is not None:  # small job: answer the request with the normal result
        return result(request_id, export_result(year, month, 1_184, False))

    # A whole year is a long job. Only a client that declared the extension may get a task.
    if TASKS_EXT not in capabilities.get("extensions", {}):
        return error(request_id, -32021, "Missing required client capability",
                     {"requiredCapabilities": {"extensions": {TASKS_EXT: {}}}})
    created = now()
    task = {"taskId": secrets.token_urlsafe(16), "owner": user, "status": "working",
            "statusMessage": "Export started.", "createdAt": created, "lastUpdatedAt": created,
            "ttlMs": TASK_TTL_MS, "pollIntervalMs": POLL_INTERVAL_MS, "answers": {}, "cancelRequested": False}
    tasks[task["taskId"]] = task  # stored before the response, so tasks/get works at once
    can_elicit = "elicitation" in capabilities
    task["job"] = asyncio.get_running_loop().create_task(run_year_export(task, year, can_elicit))
    return result(request_id, {**public_view(task), "resultType": "task"})


async def handle(message: dict, user: str) -> dict:
    request_id, method = message.get("id"), message.get("method")
    params = message.get("params", {})
    meta = params.get("_meta", {})
    capabilities = meta["io.modelcontextprotocol/clientCapabilities"]  # checked in mcp()

    if method == "server/discover":
        return result(request_id, {"supportedVersions": [PROTOCOL_VERSION],
                                   "capabilities": {"tools": {}, "extensions": {TASKS_EXT: {}}},
                                   "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO}})
    if method == "tools/list":
        return result(request_id, {"tools": [EXPORT_TOOL], "ttlMs": 300000, "cacheScope": "public"})
    if method == "tools/call":
        return call_tool(request_id, params, capabilities, user)

    if method in ("tasks/get", "tasks/update", "tasks/cancel"):
        if TASKS_EXT not in capabilities.get("extensions", {}):
            return error(request_id, -32021, "Missing required client capability",
                         {"requiredCapabilities": {"extensions": {TASKS_EXT: {}}}})
        task, failure = find_task(request_id, params, user)
        if failure:
            return failure
        if method == "tasks/get":
            return result(request_id, public_view(task))
        if method == "tasks/update":
            outstanding = task.get("inputRequests", {})
            for key, answer in params.get("inputResponses", {}).items():
                if key in outstanding and key not in task["answers"]:  # ignore unknown or answered keys
                    task["answers"][key] = answer
            return result(request_id, {})
        task["cancelRequested"] = True  # tasks/cancel: acknowledge, the job stops at its next check
        return result(request_id, {})
    return error(request_id, -32601, "Method not found")


@app.post("/mcp")
async def mcp(request: Request):
    user = USERS.get(request.headers.get("Authorization", "").removeprefix("Bearer "))
    if user is None:
        return JSONResponse({"error": "invalid_token"}, status_code=401,
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    message = await request.json()
    params = message.get("params", {})
    # Streamable HTTP routing headers: Mcp-Method always, Mcp-Name = taskId for tasks/* requests.
    expected = {"Mcp-Method": message.get("method")}
    if str(message.get("method", "")).startswith("tasks/"):
        expected["Mcp-Name"] = params.get("taskId")
    elif message.get("method") == "tools/call":
        expected["Mcp-Name"] = params.get("name")
    for header, value in expected.items():
        if request.headers.get(header) != value:
            return JSONResponse(error(message.get("id"), -32020, f"Header mismatch: {header}"), status_code=400)
    meta = params.get("_meta", {})
    if meta.get("io.modelcontextprotocol/protocolVersion") != PROTOCOL_VERSION \
            or "io.modelcontextprotocol/clientCapabilities" not in meta:
        return JSONResponse(error(message.get("id"), -32602, "Missing or unsupported _meta fields"), status_code=400)
    reply = await handle(message, user)
    # A missing capability is answered with HTTP 400, as the 2026-07-28 spec requires
    status = 400 if reply.get("error", {}).get("code") == -32021 else 200
    return JSONResponse(reply, status_code=status)
