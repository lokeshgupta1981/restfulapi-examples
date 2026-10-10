"""Measures how many tokens each interface puts into the model's context for one task:
"What is the total of the paid orders of customer C-5?"

Token counts use tiktoken with the o200k_base encoding. Other models count differently,
so compare the ratios, not the absolute numbers.
"""
import asyncio
import json
import subprocess
import sys

import tiktoken
from mcp import Client, StdioServerParameters

enc = tiktoken.get_encoding("o200k_base")
PY = sys.executable


def tokens(text):
    return len(enc.encode(text))


def cli(*args):
    return subprocess.run([PY, "orders_cli.py", *args], capture_output=True, text=True, check=True).stdout


async def main():
    rows = []
    server = StdioServerParameters(command=PY, args=["orders_mcp_server.py"])
    async with Client(server) as client:
        listed = await client.list_tools()
        # A host passes name, description and input schema of each tool to the model.
        definitions = json.dumps([
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in listed.tools
        ])
        rows.append(("MCP", "tool definitions (3 tools), in context from the start", tokens(definitions)))

        result = await client.call_tool("list_orders", {"customer_id": "C-5", "status": "paid"})
        # The Python SDK returns one text block per order and the same data in structuredContent.
        text = "\n".join(block.text for block in result.content if block.type == "text")
        rows.append(("MCP", "list_orders result (full orders)", tokens(text)))
        mcp_total = round(sum(o["total"] for o in result.structured_content["result"]), 2)

        slim_result = await client.call_tool(
            "list_orders", {"customer_id": "C-5", "status": "paid", "fields": ["id", "total"]})
        slim_text = "\n".join(block.text for block in slim_result.content if block.type == "text")
        rows.append(("MCP", "list_orders result with fields=[id, total]", tokens(slim_text)))

    help_text = cli("--help") + cli("list", "--help")
    rows.append(("CLI", "orders --help + orders list --help, when the model runs them", tokens(help_text)))

    table = cli("list", "--customer", "C-5", "--status", "paid")
    rows.append(("CLI", "list output (table)", tokens(table)))

    slim = cli("list", "--customer", "C-5", "--status", "paid", "--fields", "id,total", "--json")
    rows.append(("CLI", "list output with --fields id,total --json", tokens(slim)))
    cli_total = round(sum(o["total"] for o in json.loads(slim)), 2)

    # Code mode: the model writes a short script, the script calls the tool,
    # and only the printed sum goes back to the model.
    script = ('orders = await mcp.list_orders(customer_id="C-5", status="paid")\n'
              'print(round(sum(o["total"] for o in orders), 2))')
    rows.append(("Code mode", "script written by the model + printed result",
                 tokens(script) + tokens(str(mcp_total))))

    for kind, what, n in rows:
        print(f"{kind:<10} {what:<60} {n:>5} tokens")
    print(f"\nanswer via MCP: {mcp_total} EUR, via CLI: {cli_total} EUR")


asyncio.run(main())
