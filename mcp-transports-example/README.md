Source code for the article [MCP Transports, stdio vs Streamable HTTP](https://restfulapi.net/mcp-transports-stdio-vs-streamable-http/)

# MCP transports example

One small MCP server (protocol version 2026-07-28) with two transport bindings, and a client that sends the same requests over both and prints the wire traffic. No MCP SDK is used, so every line on the wire is visible.

- `core.py` holds the server logic: `server/discover`, `tools/list` and two tools. It does not know which transport carries the messages.
- `stdio_server.py` reads one JSON-RPC message per line from stdin and writes the replies to stdout. Logs go to stderr.
- `http_server.py` serves `POST /mcp` with FastAPI. It checks the `Origin`, `MCP-Protocol-Version`, `Mcp-Method` and `Mcp-Name` headers, answers with JSON or with an SSE stream when the client asked for progress, and answers `GET` and `DELETE` with HTTP 405.

## Versions

Python 3.13, fastapi 0.143.0, uvicorn 0.54.0. `run_demo.sh` also uses curl.

## Files

| File | What it does |
| --- | --- |
| `core.py` | Transport-independent request handling. |
| `stdio_server.py` | stdio binding. |
| `http_server.py` | Streamable HTTP binding on port 8000. |
| `client.py` | `stdio`, `http` and `http-errors` commands. |
| `run_demo.sh` | Runs all three commands. |
| `OUTPUTS.txt` | Output of `run_demo.sh` from a real run. |

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_demo.sh                    # Windows: run in Git Bash or WSL
```
