Source code for the article [MCP Security Risks and Best Practices](https://restfulapi.net/mcp-security/)

# MCP security example

A small MCP server (Streamable HTTP, protocol version 2026-07-28) and a client-side guard that show the main MCP security controls:

- The server rejects an unknown `Origin` header with HTTP 403 (DNS rebinding protection).
- The server accepts only tokens issued for it (audience check) and returns HTTP 401 for any other token.
- Each tool needs its own scope. A missing scope gets HTTP 403 with `WWW-Authenticate: Bearer error="insufficient_scope", scope="..."`.
- Carts are state handles: random IDs, stored under `<user_id>:<cart_id>`, so another user's token cannot use them.
- The client pins a SHA-256 hash of every approved tool definition and reports changed tools (rug pulls) and suspicious text in tool descriptions.

The demo signs test tokens with a shared secret (`tokens.py`) so it runs without an OAuth authorization server. A real MCP server validates tokens from its authorization server with the server's public keys.

## Versions

Python 3.13, fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1.

## Files

| File | What it does |
| --- | --- |
| `server.py` | The MCP endpoint `POST /mcp` with the tools `create_cart`, `add_item` and `checkout`. `RUG_PULL=1` serves a changed `add_item` description. |
| `tokens.py` | Mints test access tokens with a subject, scopes and an audience. |
| `client_guard.py` | `pin`, `check` and `call` commands for the client-side checks. |
| `run_demo.sh` | Starts the server and runs every case. |
| `OUTPUTS.txt` | Output of `run_demo.sh` from a real run. |

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_demo.sh                    # Windows: run in Git Bash or WSL
```

To try single calls, start the server with `uvicorn server:app --host 127.0.0.1 --port 8000`, mint a token with `python tokens.py --sub alice --scope "cart:write"` and pass it to `client_guard.py` with `--token`.
