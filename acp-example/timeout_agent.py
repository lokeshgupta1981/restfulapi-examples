"""A small ACP agent. It adds timeout=10 to requests.get() calls in one Python file.

The agent has no language model. It follows the same ACP message flow as a real
coding agent, so an editor can show its plan, its tool calls and its diff.
Run it from an ACP client (an editor), not by hand: python timeout_agent.py
"""
import asyncio
import re
import uuid
from pathlib import Path

from acp import (
    PROTOCOL_VERSION,
    Agent,
    InitializeResponse,
    NewSessionResponse,
    PromptResponse,
    run_agent,
    start_edit_tool_call,
    text_block,
    tool_diff_content,
    update_agent_message_text,
    update_plan,
    plan_entry,
    update_tool_call,
)
from acp.schema import AgentCapabilities, Implementation, PermissionOption

CALL = re.compile(r"requests\.get\(([^()]*(?:\([^()]*\))?[^()]*)\)")


def add_timeouts(source):
    """Return the new source and the number of changed calls."""
    changed = 0

    def fix(match):
        nonlocal changed
        if "timeout=" in match.group(1):
            return match.group(0)
        changed += 1
        return f"requests.get({match.group(1)}, timeout=10)"

    return CALL.sub(fix, source), changed


class TimeoutAgent(Agent):
    def on_connect(self, conn):
        self.client = conn  # used to call the editor: fs/*, session/update, request_permission

    async def initialize(self, protocol_version, client_capabilities=None, client_info=None, **kwargs):
        self.can_read = bool(client_capabilities and client_capabilities.fs and client_capabilities.fs.read_text_file)
        self.can_write = bool(client_capabilities and client_capabilities.fs and client_capabilities.fs.write_text_file)
        return InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(load_session=False),
            agent_info=Implementation(name="timeout-agent", title="Timeout Agent", version="1.0.0"),
        )

    async def new_session(self, cwd, mcp_servers=None, **kwargs):
        self.cwd = cwd
        return NewSessionResponse(session_id=f"sess_{uuid.uuid4().hex[:12]}")

    async def prompt(self, session_id, prompt, **kwargs):
        text = " ".join(block.text for block in prompt if getattr(block, "type", "") == "text")
        found = re.search(r"[\w./-]+\.py", text)
        if not found:
            await self.say(session_id, "Name a Python file, for example: add timeouts to weather.py")
            return PromptResponse(stop_reason="end_turn")
        path = str(Path(self.cwd, found.group(0)))

        await self.client.session_update(session_id, update_plan([
            plan_entry("Read " + found.group(0), priority="medium", status="in_progress"),
            plan_entry("Add timeout=10 to requests.get() calls", priority="high", status="pending"),
        ]))

        # Read the file through the editor, so unsaved changes in the editor are included.
        old_text = (await self.client.read_text_file(session_id=session_id, path=path)).content
        new_text, changed = add_timeouts(old_text)
        if changed == 0:
            await self.say(session_id, "All requests.get() calls already have a timeout.")
            return PromptResponse(stop_reason="end_turn")

        call_id = "call_" + uuid.uuid4().hex[:8]
        await self.client.session_update(session_id, start_edit_tool_call(
            call_id, f"Add timeouts in {found.group(0)}", path, new_text))
        await self.client.session_update(session_id, update_tool_call(
            call_id, content=[tool_diff_content(path, new_text, old_text)]))

        # Ask the user before changing the file.
        answer = await self.client.request_permission(
            session_id=session_id,
            tool_call=update_tool_call(call_id),
            options=[
                PermissionOption(option_id="allow", name="Allow once", kind="allow_once"),
                PermissionOption(option_id="reject", name="Reject", kind="reject_once"),
            ],
        )
        if getattr(answer.outcome, "option_id", None) != "allow":
            await self.client.session_update(session_id, update_tool_call(call_id, status="failed"))
            await self.say(session_id, "No changes made.")
            return PromptResponse(stop_reason="end_turn")

        await self.client.write_text_file(session_id=session_id, path=path, content=new_text)
        await self.client.session_update(session_id, update_tool_call(call_id, status="completed"))
        await self.say(session_id, f"Added timeout=10 to {changed} requests.get() calls in {found.group(0)}.")
        return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id, **kwargs):
        pass

    async def say(self, session_id, text):
        await self.client.session_update(session_id, update_agent_message_text(text))


if __name__ == "__main__":
    asyncio.run(run_agent(TimeoutAgent()))
