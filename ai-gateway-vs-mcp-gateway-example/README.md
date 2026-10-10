Source code for the article [AI Gateway vs MCP Gateway](https://restfulapi.net/ai-gateway-vs-mcp-gateway/)

# AI gateway and MCP gateway example

Two small gateways in one FastAPI app, with stand-in backends, so the demo runs without any API key.

- The AI gateway (`POST /v1/chat/completions`, OpenAI-compatible) checks a virtual key per team, maps a model alias to providers, falls back to the next provider when one fails, enforces a token budget per minute (HTTP 429 with `Retry-After`) and logs tokens and cost per team.
- The MCP gateway (`POST /mcp`, Streamable HTTP, protocol version 2026-07-28) puts two MCP servers behind one endpoint, prefixes tool names with the server name, filters `tools/list` and `tools/call` per team, logs every call, and calls the servers with its own service token instead of the client's token.

## Versions

Python 3.13, fastapi 0.143.0, uvicorn 0.54.0. `run_demo.sh` also uses curl.

## Files

| File | What it does |
| --- | --- |
| `gateway.py` | Both gateways on port 8000. |
| `backends.py` | Two fake LLM providers and two fake MCP servers on port 9001. |
| `demo.py` | Sends one request to a gateway and prints the result. |
| `run_demo.sh` | Starts both apps and runs every case. |
| `OUTPUTS.txt` | Output of `run_demo.sh` from a real run. |

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_demo.sh                    # Windows: run in Git Bash or WSL
```

The token budget is counted per clock minute. If the demo starts in the last seconds of a minute, case 3 can land in a new minute and succeed.
