"""Curated MCP server for the Helpdesk API.

- Operations marked with x-mcp-tool in openapi.yaml are exposed under the name
  and description given there. Every other operation is left out.
- Four task-level tools are written by hand and call several endpoints.

Run over stdio:            python curated_server.py
Run over Streamable HTTP:  python curated_server.py http
"""
import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path
from typing import Annotated, Literal

import httpx2
import yaml
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.providers.openapi import MCPType, OpenAPITool, RouteMap
from fastmcp.utilities.openapi import HTTPRoute
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

spec = yaml.safe_load((Path(__file__).parent / "openapi.yaml").read_text())

api_client = httpx2.AsyncClient(
    base_url=os.environ.get("HELPDESK_API_URL", spec["servers"][0]["url"]),
    headers={"Authorization": f"Bearer {os.environ['HELPDESK_API_TOKEN']}"},
    timeout=10,
)


# 1. Generated part: only operations with an x-mcp-tool extension become tools.
def only_flagged(route: HTTPRoute, mcp_type: MCPType) -> MCPType:
    return MCPType.TOOL if "x-mcp-tool" in route.extensions else MCPType.EXCLUDE


def apply_x_mcp(route: HTTPRoute, tool: OpenAPITool) -> None:
    tool.description = route.extensions["x-mcp-tool"]["description"]
    tool.annotations = ToolAnnotations(readOnlyHint=route.method == "GET")


tool_names = {
    operation["operationId"]: operation["x-mcp-tool"]["name"]
    for path_item in spec["paths"].values()
    for operation in path_item.values()
    if isinstance(operation, dict) and "x-mcp-tool" in operation
}

mcp = FastMCP.from_openapi(
    openapi_spec=spec,
    client=api_client,
    name="helpdesk-curated",
    route_maps=[RouteMap(mcp_type=MCPType.EXCLUDE)],
    route_map_fn=only_flagged,
    mcp_component_fn=apply_x_mcp,
    mcp_names=tool_names,
)


# 2. Hand-written task-level tools.
async def call_api(method: str, path: str, **kwargs):
    resp = await api_client.request(method, path, **kwargs)
    if resp.status_code >= 400:
        raise ToolError(f"HTTP {resp.status_code}: {resp.json().get('detail', resp.text)}")
    return resp.json() if resp.content else None


class TicketRow(BaseModel):
    id: str
    subject: str
    status: str
    priority: str
    assignee: str | None
    customer_id: str


class FoundTickets(BaseModel):
    tickets: list[TicketRow]
    more_available: bool


class CommentRow(BaseModel):
    kind: str
    author: str
    created_at: str
    body: str


class TicketOverview(BaseModel):
    ticket: TicketRow
    customer_name: str
    customer_plan: str
    comments: list[CommentRow]


class CloseResult(BaseModel):
    status: Literal["needs_confirmation", "closed"]
    message: str
    confirmation: str | None = None


# A new secret on every server start, so a code works only for this server process.
CONFIRM_SECRET = secrets.token_bytes(32)


def confirmation_code(ticket_id: str, resolution: str) -> str:
    message = f"{ticket_id}|{resolution}".encode()
    return hmac.new(CONFIRM_SECRET, message, hashlib.sha256).hexdigest()[:12]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def find_tickets(
    status: Literal["open", "pending", "closed"] | None = None,
    priority: Literal["low", "normal", "high", "urgent"] | None = None,
    assignee: Annotated[str | None, Field(description="Agent id from list_agents, for example A-2")] = None,
    customer_id: Annotated[str | None, Field(description="Customer id, for example C-201")] = None,
    max_results: Annotated[int, Field(ge=1, le=50)] = 20,
) -> FoundTickets:
    """Find tickets, newest first. All filters are optional.
    Returns short rows; call get_ticket_overview for the full ticket and its comments."""
    filters = {"status": status, "priority": priority, "assignee": assignee, "customer_id": customer_id}
    params = {k: v for k, v in filters.items() if v}
    rows, cursor = [], None
    while len(rows) < max_results:
        page = await call_api("GET", "/tickets", params={**params, **({"cursor": cursor} if cursor else {})})
        rows += page["items"]
        cursor = page["next_cursor"]
        if not cursor:
            break
    return FoundTickets(
        tickets=[TicketRow(**t) for t in rows[:max_results]],
        more_available=len(rows) > max_results or cursor is not None,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_ticket_overview(ticket_id: str) -> TicketOverview:
    """Get one ticket with its customer and all comments, oldest comment first.
    Ticket ids look like T-1004."""
    ticket = await call_api("GET", f"/tickets/{ticket_id}")
    customer = await call_api("GET", f"/customers/{ticket['customer_id']}")
    comments = await call_api("GET", f"/tickets/{ticket_id}/comments")
    return TicketOverview(
        ticket=TicketRow(**ticket),
        customer_name=customer["name"],
        customer_plan=customer["plan"],
        comments=[CommentRow(**c) for c in comments],
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
async def reply_to_customer(ticket_id: str, message: str) -> TicketRow:
    """Email a reply to the customer and set the ticket to pending (waiting for the customer).
    Show the user the message text before calling this tool."""
    await call_api("POST", f"/tickets/{ticket_id}/comments",
                   json={"kind": "public_reply", "body": message, "notify_customer": True})
    ticket = await call_api("PATCH", f"/tickets/{ticket_id}", json={"status": "pending"})
    return TicketRow(**ticket)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False))
async def close_ticket(ticket_id: str, resolution: str, confirmation: str | None = None) -> CloseResult:
    """Close a ticket and save the resolution as an internal note.
    Call it first without confirmation and show the returned summary to the user.
    Only after the user agrees, call it again with the confirmation code from the first result."""
    ticket = await call_api("GET", f"/tickets/{ticket_id}")
    if ticket["status"] == "closed":
        return CloseResult(status="closed", message=f"{ticket_id} was already closed.")
    code = confirmation_code(ticket_id, resolution)
    if confirmation is None:
        return CloseResult(
            status="needs_confirmation",
            message=f"{ticket_id} '{ticket['subject']}' ({ticket['status']}, {ticket['priority']}) "
                    f"will be closed with the note: {resolution}. Ask the user to confirm.",
            confirmation=code,
        )
    if not hmac.compare_digest(confirmation, code):
        raise ToolError("Wrong confirmation code. Call close_ticket without a confirmation first.")
    await call_api("POST", f"/tickets/{ticket_id}/comments",
                   json={"kind": "internal_note", "body": f"Resolution: {resolution}"})
    await call_api("PATCH", f"/tickets/{ticket_id}", json={"status": "closed"})
    return CloseResult(status="closed", message=f"{ticket_id} is closed.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8002, show_banner=False)
    else:
        mcp.run(show_banner=False)
