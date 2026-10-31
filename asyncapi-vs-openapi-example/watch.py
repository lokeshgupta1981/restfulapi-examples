"""Print every message on the broker as it arrives: topic, then payload."""
import asyncio

import aiomqtt


async def main():
    async with aiomqtt.Client("localhost", 9211, identifier="watcher") as client:
        await client.subscribe("#", qos=1)
        print("[watch] listening on #", flush=True)
        async for message in client.messages:
            print(f"[watch] {message.topic}\n{message.payload.decode()}", flush=True)


asyncio.run(main())
