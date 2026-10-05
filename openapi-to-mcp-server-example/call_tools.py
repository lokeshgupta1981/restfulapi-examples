"""Call the same jobs on both MCP servers and print what an agent would get back.

Run: python call_tools.py   (the Helpdesk API must be running on port 8080)
"""
import asyncio
import json
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def server(script: str) -> Client:
    env = {"HELPDESK_API_TOKEN": os.environ["HELPDESK_API_TOKEN"]}
    return Client(StdioTransport(command=sys.executable, args=[script], env=env))


async def call(client: Client, name: str, args: dict) -> None:
    result = await client.call_tool(name, args, raise_on_error=False)
    text = result.content[0].text if result.content else ""
    print(f"> {name} {json.dumps(args)}")
    print(f"  is_error={result.is_error}")
    print(f"  {text[:300] or '(empty result)'}")


async def main() -> None:
    print("== generated server")
    async with server("generated_server.py") as client:
        result = await client.call_tool("listTickets", {"status": "open"})
        page = result.structured_content
        print(f"> listTickets {{\"status\": \"open\"}}")
        print(f"  {len(page['items'])} tickets, next_cursor={page['next_cursor']}")
        await call(client, "addComment", {"ticket_id": "T-1003"})
        await call(client, "deleteTicket", {"ticket_id": "T-1024"})
        await call(client, "getTicket", {"ticket_id": "T-1024"})

    print("== curated server")
    async with server("curated_server.py") as client:
        result = await client.call_tool("find_tickets", {"status": "open"})
        found = result.structured_content
        print(f"> find_tickets {{\"status\": \"open\"}}")
        print(f"  {len(found['tickets'])} tickets, more_available={found['more_available']}")
        await call(client, "get_ticket_overview", {"ticket_id": "T-1005"})
        await call(client, "reply_to_customer", {"ticket_id": "T-1003",
                                                 "message": "We corrected the VAT number on your invoice."})
        close = {"ticket_id": "T-1005", "resolution": "Webhook URL fixed"}
        await call(client, "close_ticket", {**close, "confirmation": "123456abcdef"})
        first = await client.call_tool("close_ticket", close)
        code = first.structured_content["confirmation"]
        print(f"> close_ticket {json.dumps(close)}")
        print(f"  {json.dumps(first.structured_content)}")
        await call(client, "close_ticket", {**close, "confirmation": code})
        await call(client, "deleteTicket", {"ticket_id": "T-1023"})


asyncio.run(main())
