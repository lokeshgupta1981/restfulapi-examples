"""Shipping service: receives order events and checks each one against the
Orders service's asyncapi.yaml (the Orders service owns these channels)."""
import asyncio
import json

import aiomqtt

from contract import Contract

contract = Contract()


async def main():
    async with aiomqtt.Client("localhost", 9211, identifier="shipping-service") as client:
        for channel_id in ("orderPlaced", "orderStatus"):
            await client.subscribe(contract.subscription(channel_id), qos=1)
        print("[shipping] listening", flush=True)
        async for message in client.messages:
            topic = str(message.topic)
            payload = json.loads(message.payload)
            name, errors = contract.check(topic, payload)
            if errors:
                print(f"[shipping] REJECTED {topic} as {name}: {errors}", flush=True)
            else:
                print(f"[shipping] valid {name} on {topic}", flush=True)


asyncio.run(main())
