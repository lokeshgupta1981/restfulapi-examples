"""Small test client for the task tracker MCP server.

python client.py stdio   starts server.py as a subprocess
python client.py http    connects to a running `python server.py --http`
"""

import asyncio
import sys

from mcp import Client, StdioServerParameters


def server_target(mode: str):
    if mode == "http":
        return "http://127.0.0.1:8040/mcp"
    return StdioServerParameters(command=sys.executable, args=["server.py"])


async def show_progress(progress: float, total: float | None, message: str | None) -> None:
    print(f"  progress {progress:.0f}/{total:.0f}: {message}")


async def main(mode: str) -> None:
    async with Client(server_target(mode)) as client:
        print("protocol:", client.protocol_version)
        print("server:", client.server_info.name, client.server_info.version)

        tools = await client.list_tools()
        print("tools:", [tool.name for tool in tools.tools])

        result = await client.call_tool("search_tasks", {"project": "APP", "status": "todo"})
        print("search_tasks ->", result.structured_content)

        result = await client.call_tool("complete_task", {"task_id": 4})
        print("complete_task(4) -> is_error:", result.is_error, "|", result.content[0].text)

        result = await client.call_tool(
            "project_report",
            {"project": "APP", "today": "2026-10-10"},
            progress_callback=show_progress,
        )
        print("project_report ->", result.structured_content)

        resource = await client.read_resource("tasks://projects/WEB/summary")
        print("resource ->")
        print(resource.contents[0].text)

        prompt = await client.get_prompt("weekly_update", {"project": "WEB"})
        print("prompt ->", prompt.messages[0].content.text)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "stdio"))
