"""A minimal ACP client that plays the editor. It starts the agent as a subprocess,
prints every JSON-RPC message on the wire, serves file reads and writes from the
workspace folder, and asks you before the agent changes a file.
Each run copies samples/weather.py into a fresh workspace folder.

Usage:
  python mini_editor.py "add timeouts to weather.py"
  python mini_editor.py --yes "add timeouts to weather.py"    # approve without asking
"""
import asyncio
import json
import shutil
import sys
from pathlib import Path

from acp import (
    PROTOCOL_VERSION,
    Client,
    ReadTextFileResponse,
    RequestPermissionResponse,
    WriteTextFileResponse,
    spawn_agent_process,
    text_block,
)
from acp.schema import (
    AllowedOutcome,
    ClientCapabilities,
    DeniedOutcome,
    FileSystemCapabilities,
    Implementation,
)

HERE = Path(__file__).parent
WORKSPACE = HERE / "workspace"
AUTO_YES = "--yes" in sys.argv


def show_wire(event):
    arrow = "editor -> agent" if event.direction.value == "outgoing" else "agent -> editor"
    text = json.dumps(event.message)
    print(f"  [{arrow}] {text[:150]}{' ...' if len(text) > 150 else ''}")


class MiniEditor(Client):
    async def session_update(self, session_id, update, **kwargs):
        kind = update.session_update
        if kind == "agent_message_chunk":
            print(f"AGENT: {update.content.text}")
        elif kind == "plan":
            for entry in update.entries:
                print(f"PLAN: [{entry.status}] {entry.content}")
        elif kind in ("tool_call", "tool_call_update"):
            if update.status:
                title = f"{update.title} " if update.title else ""
                print(f"TOOL {update.tool_call_id}: {title}({update.status})")
            for item in update.content or []:
                if item.type == "diff":
                    print(f"DIFF {Path(item.path).name}:")
                    for old, new in zip(item.old_text.splitlines(), item.new_text.splitlines()):
                        if old != new:
                            print(f"  - {old.strip()}\n  + {new.strip()}")

    async def request_permission(self, session_id, tool_call, options, **kwargs):
        choices = ", ".join(f"{o.option_id} ({o.name})" for o in options)
        if AUTO_YES:
            choice = options[0].option_id
            print(f"PERMISSION: {choices} -> {choice} (--yes)")
        else:
            choice = input(f"PERMISSION: {choices}. Type an option: ").strip()
        if choice not in {o.option_id for o in options}:
            return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))
        return RequestPermissionResponse(outcome=AllowedOutcome(outcome="selected", option_id=choice))

    async def read_text_file(self, session_id, path, line=None, limit=None, **kwargs):
        return ReadTextFileResponse(content=Path(path).read_text())

    async def write_text_file(self, session_id, path, content, **kwargs):
        Path(path).write_text(content)
        return WriteTextFileResponse()


async def main():
    prompt = [a for a in sys.argv[1:] if a != "--yes"]
    prompt = prompt[0] if prompt else "add timeouts to weather.py"
    shutil.rmtree(WORKSPACE, ignore_errors=True)
    shutil.copytree(HERE / "samples", WORKSPACE)
    agent = HERE / "timeout_agent.py"
    async with spawn_agent_process(MiniEditor(), sys.executable, str(agent), observers=[show_wire]) as (conn, proc):
        init = await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(fs=FileSystemCapabilities(read_text_file=True, write_text_file=True)),
            client_info=Implementation(name="mini-editor", title="Mini Editor", version="1.0.0"),
        )
        print(f"Connected to {init.agent_info.name}, ACP protocol version {init.protocol_version}")
        session = await conn.new_session(cwd=str(WORKSPACE.resolve()), mcp_servers=[])
        print(f"USER: {prompt}")
        result = await conn.prompt(session_id=session.session_id, prompt=[text_block(prompt)])
        print(f"Turn ended: {result.stop_reason}")


if __name__ == "__main__":
    asyncio.run(main())
