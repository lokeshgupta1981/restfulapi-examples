Source code for the article [MCP Tasks for Long-Running Tool Calls](https://restfulapi.net/mcp-tasks-extension/)

# MCP tasks example

An MCP server for an accounting app with one long-running tool, and a client that drives MCP tasks. Both use protocol version 2026-07-28 and the official Tasks extension (`io.modelcontextprotocol/tasks`) over Streamable HTTP, written without an SDK so every request and result is visible.

- `server.py` (FastAPI, port 8000) offers the tool `export_invoices`.
  - One month is exported inside the `tools/call` request and returns the normal tool result.
  - A whole year returns a task (`resultType: "task"`) and runs as a background job. In July the task asks whether customer emails may be included (status `input_required`), but only when the request declared the `elicitation` capability.
  - It answers `tasks/get`, `tasks/update` and `tasks/cancel` (cooperative cancel), and returns `-32021` with HTTP 400 when a client without the extension asks for a year export.
  - Year 2019 ends as a `failed` task with a JSON-RPC error, and a future year returns a normal tool result with `isError: true`.
  - Task ids come from `secrets.token_urlsafe(16)`, and each task belongs to the user of the bearer token, so another user gets "Task not found".
- `client.py` sends every request with the 2026-07-28 `_meta` fields and the `Mcp-Method` and `Mcp-Name` headers, polls with `pollIntervalMs`, answers the input request once and runs every case.

The bearer tokens in `server.py` are demo values.

## Versions

Python 3.10 or later (tested with Python 3.13), FastAPI 0.143.0, Uvicorn 0.54.0. The client uses only the standard library. `run_demo.sh` also needs curl.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: run the script in Git Bash or WSL
pip install -r requirements.txt
./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run. Task ids and timestamps change on every run.
