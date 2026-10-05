"""MCP client that signs in with OAuth through the mcp SDK's OAuthClientProvider.

It prints every HTTP request the client sends, so we can follow the flow:
401 -> metadata discovery -> authorization (PKCE) -> token -> retry,
and later 403 insufficient_scope -> step-up authorization -> retry.

A desktop app opens the authorization URL in the browser and runs a small
callback server on the redirect URI. This demo has no browser: it sends the
authorization request itself and reads the code from the redirect response.
"""

import asyncio
import json
from urllib.parse import parse_qs, urlparse

import httpx2
from mcp import Client
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.auth.oauth2 import AuthorizationCodeResult
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

MCP_SERVER_URL = "http://127.0.0.1:9410/mcp"
REDIRECT_URI = "http://127.0.0.1:9499/callback"


class MemoryStorage(TokenStorage):
    """Keeps tokens in memory. The client is pre-registered as orders-desktop."""

    def __init__(self) -> None:
        self.tokens: OAuthToken | None = None
        self.client_info = OAuthClientInformationFull(
            client_id="orders-desktop",
            redirect_uris=[REDIRECT_URI],
            token_endpoint_auth_method="none",
        )

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens
        print(f"    token received: scope={tokens.scope!r} expires_in={tokens.expires_in}")

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info


class HeadlessBrowser:
    """Stands in for the browser and the redirect URI callback server."""

    def __init__(self) -> None:
        self.callback_url = ""

    async def open(self, authorization_url: str) -> None:
        query = parse_qs(urlparse(authorization_url).query)
        shown = {k: query[k][0] for k in ("client_id", "scope", "resource", "code_challenge_method")}
        print(f"    browser opens /authorize with {json.dumps(shown)}")
        async with httpx2.AsyncClient() as http:
            response = await http.get(authorization_url)  # the demo user approves
        self.callback_url = response.headers["location"]

    async def callback(self) -> AuthorizationCodeResult:
        query = parse_qs(urlparse(self.callback_url).query)
        print(f"    redirect back to {REDIRECT_URI} with code, state and iss={query['iss'][0]}")
        return AuthorizationCodeResult(code=query["code"][0], state=query["state"][0], iss=query["iss"][0])


async def log_request(request: httpx2.Request) -> None:
    line = f"--> {request.method} {request.url.copy_with(query=None)}"
    if request.url.path == "/mcp" and request.method == "POST":
        rpc = json.loads(request.content)
        tool = rpc.get("params", {}).get("name")
        line += f"  {rpc['method']}{' ' + tool if tool else ''}"
    if "authorization" in request.headers:
        line += "  (Bearer token)"
    print(line)


async def log_response(response: httpx2.Response) -> None:
    print(f"<-- HTTP {response.status_code}")
    if response.status_code in (401, 403):
        print(f"    WWW-Authenticate: {response.headers['www-authenticate']}")


async def main() -> None:
    browser = HeadlessBrowser()
    oauth = OAuthClientProvider(
        server_url=MCP_SERVER_URL,
        client_metadata=OAuthClientMetadata(
            client_name="Orders Desktop",
            redirect_uris=[REDIRECT_URI],
            grant_types=["authorization_code"],
            token_endpoint_auth_method="none",
        ),
        storage=MemoryStorage(),
        redirect_handler=browser.open,
        callback_handler=browser.callback,
    )
    http_client = httpx2.AsyncClient(
        auth=oauth, event_hooks={"request": [log_request], "response": [log_response]}
    )

    async with http_client, Client(streamable_http_client(MCP_SERVER_URL, http_client=http_client)) as client:
        print("\n== call list_orders")
        result = await client.call_tool("list_orders", {})
        print(f"    result: {json.dumps(result.structured_content)}")

        print("\n== call cancel_order")
        result = await client.call_tool("cancel_order", {"order_id": "ord_1002"})
        print(f"    result: {json.dumps(json.loads(result.content[0].text))}")


if __name__ == "__main__":
    asyncio.run(main())
