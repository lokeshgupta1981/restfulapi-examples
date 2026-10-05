Source code for the article [From OpenAPI to an MCP Server: Generated vs Curated Tools](https://restfulapi.net/openapi-to-mcp-server/)

One OpenAPI 3.1 document (`openapi.yaml`) for a small Helpdesk API, the running API, and three MCP servers built from the same document:

| File | What it is |
|---|---|
| `openapi.yaml` | OpenAPI 3.1 document: 11 operations, `$ref`, `oneOf` with a discriminator, bearer auth, tags and an `x-mcp-tool` extension |
| `helpdesk_api.py` | FastAPI app that implements the document (in-memory data, 24 tickets) |
| `generated_server.py` | Every operation becomes a tool (`FastMCP.from_openapi`) |
| `filtered_server.py` | Generated, but without `admin` operations and without `DELETE` |
| `curated_server.py` | Only operations marked with `x-mcp-tool`, plus four hand-written task-level tools |
| `compare_tools.py` | Lists the tools of all three servers and measures their size in bytes and tokens |
| `call_tools.py` | Calls the same jobs on the generated and the curated server |
| `check_ts_server.py` | Lists and calls the TypeScript server that openapi-mcp-generator creates from the same document |

## Versions

- Python 3.13 (3.10 or newer works)
- fastmcp 4.0.11 (installs mcp 2.3.0, MCP protocol version 2026-07-28)
- httpx2 2.13.1, fastapi 0.142.2, uvicorn 0.54.0, pyyaml 6.0.3, tiktoken 0.14.0

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Terminal 1, the REST API on port 8080 (it reads `HELPDESK_API_TOKEN` and uses `dev-token-123` when the variable is not set):

```bash
source .venv/bin/activate
export HELPDESK_API_TOKEN=dev-token-123   # Windows: set HELPDESK_API_TOKEN=dev-token-123
uvicorn helpdesk_api:app --port 8080
```

Terminal 2, the test clients (they start each MCP server over stdio and pass the token to it in `env`):

```bash
source .venv/bin/activate
export HELPDESK_API_TOKEN=dev-token-123
python compare_tools.py
python call_tools.py
```

`compare_tools.py` also writes the full tool lists to `tools-generated.json`, `tools-filtered.json` and `tools-curated.json`.

Restart the API before running `call_tools.py` again, because the calls delete T-1024, reply on T-1003 and close T-1005.

To run a server over Streamable HTTP instead of stdio:

```bash
python generated_server.py http    # http://127.0.0.1:8001/mcp
python curated_server.py http      # http://127.0.0.1:8002/mcp
```

Example host config for a stdio server (many hosts start a stdio server with a minimal environment, so pass the token in `env`):

```json
{"mcpServers": {"helpdesk": {"command": "python", "args": ["/path/to/curated_server.py"],
  "env": {"HELPDESK_API_TOKEN": "dev-token-123"}}}}
```

## Optional: a second generator (Node.js 20 or newer)

```bash
npx openapi-mcp-generator@4.1.0 --input openapi.yaml --output helpdesk-mcp
cd helpdesk-mcp && npm install && npm run build && cd ..
python check_ts_server.py helpdesk-mcp/build/index.js
```

The generated server reads the token from `BEARER_TOKEN_BEARERAUTH`; `check_ts_server.py` sets it from `HELPDESK_API_TOKEN`.

`OUTPUTS.txt` holds the output of a real run.
