"""Orders MCP server over Streamable HTTP, protected as an OAuth resource server.

- The mcp SDK serves the protected resource metadata (RFC 9728) and returns
  HTTP 401 with WWW-Authenticate when the token is missing or invalid.
- JwtTokenVerifier checks the JWT access token: signature, typ, iss, aud, exp.
- ToolScopeMiddleware returns HTTP 403 insufficient_scope when a tools/call
  request names a tool whose scope is not in the token.
"""

import json

import jwt
import uvicorn
from pydantic import AnyHttpUrl
from starlette.middleware import Middleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.routes import build_resource_metadata_url
from mcp.server.auth.settings import AuthSettings

ISSUER = "http://127.0.0.1:9420"
JWKS_URL = f"{ISSUER}/jwks.json"
RESOURCE = "http://127.0.0.1:9410/mcp"  # canonical URI of this MCP server
RESOURCE_METADATA_URL = str(build_resource_metadata_url(AnyHttpUrl(RESOURCE)))

# The scope each tool needs. Tools not listed need only the base scope.
TOOL_SCOPES = {
    "list_orders": "orders:read",
    "cancel_order": "orders:write",
}

ORDERS = {
    "ord_1001": {"id": "ord_1001", "customer": "asha", "total": "49.90", "status": "shipped"},
    "ord_1002": {"id": "ord_1002", "customer": "asha", "total": "15.00", "status": "pending"},
    "ord_2001": {"id": "ord_2001", "customer": "ravi", "total": "99.00", "status": "pending"},
}


class JwtTokenVerifier(TokenVerifier):
    """Validates JWT access tokens issued by our authorization server."""

    def __init__(self) -> None:
        # Caches the issuer's public keys; fetches again for an unknown kid.
        self.jwks_client = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=300)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            if jwt.get_unverified_header(token).get("typ") not in ("at+jwt", "application/at+jwt"):
                return None
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=ISSUER,
                audience=RESOURCE,
                leeway=30,
                options={"require": ["iss", "sub", "aud", "exp", "iat", "client_id"]},
            )
        except jwt.PyJWTError as error:
            print(f"token rejected: {type(error).__name__}: {error}", flush=True)
            return None

        return AccessToken(
            token=token,
            client_id=claims["client_id"],
            scopes=claims.get("scope", "").split(),
            expires_at=claims["exp"],
            resource=RESOURCE,
            subject=claims["sub"],
            claims=claims,
        )


class ToolScopeMiddleware:
    """Checks the per-tool scope before the MCP request reaches the tool."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, asgi_scope: Scope, receive: Receive, send: Send) -> None:
        # No valid token: let the SDK answer with HTTP 401.
        user = asgi_scope.get("user")  # set by the SDK's bearer-token middleware
        if asgi_scope["type"] != "http" or asgi_scope["method"] != "POST" or not (user and user.is_authenticated):
            await self.app(asgi_scope, receive, send)
            return

        # Read the JSON-RPC body once, then replay it to the MCP app.
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        needed = self.needed_scope(body)
        if needed and needed not in user.access_token.scopes:
            print(f"denied sub={user.access_token.subject} missing scope={needed}", flush=True)
            await self.send_insufficient_scope(send, needed)
            return

        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(asgi_scope, replay, send)

    @staticmethod
    def needed_scope(body: bytes) -> str | None:
        try:
            rpc = json.loads(body)
        except ValueError:
            return None
        if isinstance(rpc, dict) and rpc.get("method") == "tools/call":
            return TOOL_SCOPES.get(rpc.get("params", {}).get("name"))
        return None

    @staticmethod
    async def send_insufficient_scope(send: Send, needed: str) -> None:
        challenge = (
            f'Bearer error="insufficient_scope", scope="{needed}", '
            f'resource_metadata="{RESOURCE_METADATA_URL}", '
            f'error_description="This tool needs the {needed} scope"'
        )
        body = json.dumps({"error": "insufficient_scope", "scope": needed}).encode()
        await send({
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", challenge.encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


mcp = MCPServer(
    "Orders",
    token_verifier=JwtTokenVerifier(),
    auth=AuthSettings(
        issuer_url=ISSUER,  # strings keep the URL without a trailing slash
        resource_server_url=RESOURCE,
        required_scopes=["orders:read"],  # every MCP request needs at least this scope
        validate_token_resource=True,
    ),
)


@mcp.tool()
def list_orders() -> list[dict]:
    """List the orders of the signed-in customer."""
    token = get_access_token()
    print(f"tool=list_orders sub={token.subject} client_id={token.client_id}", flush=True)
    return [order for order in ORDERS.values() if order["customer"] == token.subject]


@mcp.tool()
def cancel_order(order_id: str) -> dict:
    """Cancel one pending order of the signed-in customer."""
    token = get_access_token()
    print(f"tool=cancel_order sub={token.subject} client_id={token.client_id} order={order_id}", flush=True)
    order = ORDERS.get(order_id)
    if order is None or order["customer"] != token.subject:
        raise ValueError(f"order {order_id} not found")
    if order["status"] != "pending":
        raise ValueError(f"order {order_id} is {order['status']} and cannot be cancelled")
    order["status"] = "cancelled"
    return order


app = mcp.streamable_http_app()
# Append so the check runs after the SDK's bearer-token authentication middleware.
app.user_middleware.append(Middleware(ToolScopeMiddleware))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9410, log_level="warning")
