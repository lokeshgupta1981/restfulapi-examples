"""Send one JSON message: python publish.py TOPIC 'JSON'"""
import asyncio
import sys

import aiomqtt


async def main(topic, body):
    async with aiomqtt.Client("localhost", 9211) as client:
        await client.publish(topic, body, qos=1)


asyncio.run(main(sys.argv[1], sys.argv[2]))
