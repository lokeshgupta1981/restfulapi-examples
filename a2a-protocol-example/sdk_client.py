"""Calls the same agent with the official A2A Python SDK (a2a-sdk), to check interoperability."""

import asyncio
import uuid

from a2a.client import ClientConfig, create_client
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState


async def main() -> None:
    # streaming=False makes the SDK call SendMessage instead of SendStreamingMessage
    client = await create_client("http://127.0.0.1:9999", client_config=ClientConfig(streaming=False))
    request = SendMessageRequest(message=Message(
        message_id=uuid.uuid4().hex, role=Role.ROLE_USER,
        parts=[Part(text="Check expense: taxi 95 EUR, receipt R-7781")]))
    async for event in client.send_message(request):
        task = event.task
        print("SDK SendMessage -> state:", TaskState.Name(task.status.state))
        print("artifact data:", dict(task.artifacts[0].parts[0].data.struct_value))
        print("artifact text:", task.artifacts[0].parts[1].text)
    await client.close()


asyncio.run(main())
