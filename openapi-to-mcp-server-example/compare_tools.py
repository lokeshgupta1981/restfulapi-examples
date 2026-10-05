"""List the tools of both MCP servers and measure their size.

Run: python compare_tools.py   (the Helpdesk API must be running on port 8080)
"""
import asyncio
import json
import os
import sys

import tiktoken
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ENC = tiktoken.get_encoding("o200k_base")


def server(script: str) -> Client:
    # A stdio server does not inherit our environment, so pass the token explicitly.
    env = {"HELPDESK_API_TOKEN": os.environ["HELPDESK_API_TOKEN"]}
    return Client(StdioTransport(command=sys.executable, args=[script], env=env))


def measure(tool) -> tuple[int, int]:
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    text = json.dumps(wire, separators=(",", ":"))
    return len(text.encode()), len(ENC.encode(text))


async def list_tools(script: str) -> list:
    async with server(script) as client:
        return await client.list_tools()


async def main() -> None:
    for label, script in (("generated", "generated_server.py"), ("filtered", "filtered_server.py"),
                          ("curated", "curated_server.py")):
        tools = await list_tools(script)
        with open(f"tools-{label}.json", "w") as out:
            json.dump([t.model_dump(by_alias=True, exclude_none=True) for t in tools], out, indent=2)
        rows = [(t.name, *measure(t), t.annotations) for t in tools]
        print(f"== {label}: {len(rows)} tools, "
              f"{sum(r[1] for r in rows):,} bytes, {sum(r[2] for r in rows):,} tokens")
        for name, size, tokens, ann in rows:
            hints = []
            if ann and ann.readOnlyHint:
                hints.append("readOnly")
            if ann and ann.destructiveHint:
                hints.append("destructive")
            if ann and ann.openWorldHint:
                hints.append("openWorld")
            print(f"   {name:<22} {size:>5} bytes {tokens:>5} tokens  hints: {' '.join(hints) or 'none'}")


asyncio.run(main())
