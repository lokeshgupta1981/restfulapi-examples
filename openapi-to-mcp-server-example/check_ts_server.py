"""List and call the TypeScript server made by openapi-mcp-generator.

Generate and build it first (see README), then run:
python check_ts_server.py helpdesk-mcp/build/index.js
"""
import asyncio
import json
import os
import sys

import tiktoken
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ENC = tiktoken.get_encoding("o200k_base")


async def main() -> None:
    # openapi-mcp-generator reads the token from BEARER_TOKEN_<SCHEME NAME>.
    env = {"BEARER_TOKEN_BEARERAUTH": os.environ["HELPDESK_API_TOKEN"], "PATH": os.environ["PATH"]}
    async with Client(StdioTransport(command="node", args=[sys.argv[1]], env=env)) as client:
        print("protocol:", client.session.protocol_version)
        tools = await client.list_tools()
        texts = [json.dumps(t.model_dump(by_alias=True, exclude_none=True), separators=(",", ":"))
                 for t in tools]
        print(f"{len(tools)} tools, {sum(len(t.encode()) for t in texts):,} bytes, "
              f"{sum(len(ENC.encode(t)) for t in texts):,} tokens")
        print("names:", [t.name for t in tools])
        for args in ({"ticket_id": "T-1003"},
                     {"ticket_id": "T-1003", "requestBody": {"kind": "internal_note", "body": "Checked the VAT number"}}):
            result = await client.call_tool("addComment", args, raise_on_error=False)
            print(f"> addComment {json.dumps(args)}")
            print(f"  is_error={result.is_error}")
            print("  " + result.content[0].text.replace("\n", " ")[:160])


asyncio.run(main())
