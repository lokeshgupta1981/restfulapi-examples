Source code for the article [MCP Server Authorization with OAuth: Spec and Python Example](https://restfulapi.net/mcp-server-authorization/)

A remote MCP server (Streamable HTTP, protocol 2026-07-28) protected as an OAuth resource server, following the MCP authorization specification:

- `auth_server.py`: a minimal demo authorization server (port 9420). Authorization code flow with PKCE (S256), required `resource` parameter (RFC 8707), pre-registered public client `orders-desktop`, RS256 JWT access tokens (`typ: at+jwt`, 5 minutes). There is no login page: the demo user `asha` is always signed in and always approves.
- `mcp_server.py`: the Orders MCP server (port 9410, endpoint `/mcp`). The mcp SDK serves the protected resource metadata (RFC 9728) and answers HTTP 401 with `WWW-Authenticate`. `JwtTokenVerifier` checks signature, `typ`, `iss`, `aud` and `exp`. `ToolScopeMiddleware` answers HTTP 403 `insufficient_scope` when a tool needs a scope the token does not have (`list_orders` needs `orders:read`, `cancel_order` needs `orders:write`).
- `get_token.py`: gets a token step by step (metadata, PKCE, authorize, token) for the curl demo.
- `curl_demo.sh`: the whole flow with curl, including a call with a token issued for another API.
- `client.py`: an MCP client using the SDK's `OAuthClientProvider`. It prints every HTTP request, including the step-up authorization after HTTP 403.
- `OUTPUTS.txt`: output of a real run.

Not for production: the signing key is created at startup, codes and keys live in memory, there is no user login or consent page, and everything runs on plain HTTP on 127.0.0.1. A real deployment uses HTTPS and a real authorization server (Keycloak, Auth0, Okta, Microsoft Entra ID, or similar).

## Versions

- Python 3.13.16 (the mcp SDK needs Python 3.10 or newer)
- mcp 2.3.0 (speaks MCP protocol 2026-07-28)
- httpx2 2.13.1, PyJWT 2.15.1, cryptography 50.0.2, starlette 1.7.0, uvicorn 0.54.0, pydantic 2.13.5

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# terminal 1
python auth_server.py

# terminal 2
python mcp_server.py

# terminal 3
./curl_demo.sh
python client.py
```

Restart `mcp_server.py` before running `client.py` if you want order `ord_1002` back in status `pending` (the orders live in memory).
