# MCP Server Connection Errors Example

Source code for the article [MCP Server Connection Errors, Causes and Fixes](https://restfulapi.net/mcp-server-connection-errors/).

The example reproduces the most common MCP connection failures on purpose, so we can see the exact error text a host shows for each one and test the fix.

- `servers/order_server.py` is a small stdio MCP server with one tool, `get_order_status`. The environment variable `ORDER_DESK_FAULT` turns on one mistake: `stdout` (text on stdout), `missing-key` (exits when `ORDER_API_KEY` is not set) or `slow` (the tool takes 5 seconds).
- `servers/http_server.py` serves the same tool over Streamable HTTP at `http://127.0.0.1:8000/mcp`.
- `client/check.mjs` starts or connects to a server with the official TypeScript client SDK, the way a host does, and prints the error.
- `http_probe.sh` sends one correct and eight broken HTTP requests with curl and prints the status code and body.

## Versions

- Python 3.10 or later, `mcp` 2.3.0 (protocol version 2026-07-28)
- Node.js 20 or later, `@modelcontextprotocol/client` 2.3.1
- MCP Inspector 2.10.1 (optional, run with npx)

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd client && npm install && cd ..
```

stdio scenarios (the client starts the server itself):

```bash
cd client
node check.mjs good
node check.mjs missing-command
node check.mjs stdout-text          # waits 60 seconds, set TIMEOUT_MS=10000 to wait less
node check.mjs missing-key
node check.mjs missing-key-fixed
TIMEOUT_MS=2000 node check.mjs slow
```

On Windows PowerShell, set the timeout with `$env:TIMEOUT_MS=2000` before the command. If `python3` is not the right interpreter, set `PYTHON` to its full path.

Streamable HTTP scenarios (start the server in a second terminal first):

```bash
python servers/http_server.py
./http_probe.sh
cd client
node check.mjs http-good
node check.mjs http-wrong-path
node check.mjs http-not-running
```

MCP Inspector CLI:

```bash
npx -y @modelcontextprotocol/inspector@2.10.1 --cli python servers/order_server.py --method tools/list
npx -y @modelcontextprotocol/inspector@2.10.1 --cli python servers/order_server.py -e ORDER_DESK_FAULT=missing-key --method tools/list
npx -y @modelcontextprotocol/inspector@2.10.1 --cli http://127.0.0.1:8000/mcp --transport http --method tools/call --tool-name get_order_status --tool-arg order_id=A-1001
```

## Expected output

```text
$ node check.mjs missing-command
[transport error] spawn order-desk-server ENOENT
[missing-command] Error: spawn order-desk-server ENOENT

$ node check.mjs missing-key
[server stderr] ERROR ORDER_API_KEY is not set, exiting
[missing-key] SdkError: Connection closed

$ TIMEOUT_MS=10000 node check.mjs stdout-text
[server stderr] INFO order-desk ready (fault=stdout)
[stdout-text] SdkError: Request timed out
```
