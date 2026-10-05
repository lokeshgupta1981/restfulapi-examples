"""Opens the WebSocket for order 1042, prints what arrives, and sends one
message to the server over the same connection."""

import asyncio
import json
import sys

import websockets

URL = "ws://127.0.0.1:9150/orders/1042/socket"


async def main(after: int) -> None:
    async with websockets.connect(f"{URL}?after={after}", compression=None) as socket:
        print("<", await socket.recv())
        request = json.dumps({"action": "cancel"})
        await socket.send(request)
        print(">", request)
        print("<", await socket.recv())


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 0))
