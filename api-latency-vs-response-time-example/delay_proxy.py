"""TCP proxy that adds a fixed one-way delay, so a local API behaves as if it
were across a network.

Every chunk of bytes is held for --delay-ms before it is forwarded, in both
directions. The delay is pure latency: chunks are scheduled by arrival time,
so a large download is not slowed down by the number of chunks.
The TCP handshake between the client and the proxy itself is not delayed.

Run: python3 delay_proxy.py [--listen 9201] [--target 9200] [--delay-ms 25]
"""
import argparse
import asyncio


async def pipe(reader, writer, delay):
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    async def receive():
        while True:
            data = await reader.read(65536)
            await queue.put((loop.time() + delay, data))
            if not data:
                return

    async def forward():
        while True:
            due, data = await queue.get()
            wait = due - loop.time()
            if wait > 0:
                await asyncio.sleep (wait)
            if not data:
                writer.close()
                return
            writer.write(data)
            await writer.drain()

    try:
        await asyncio.gather(receive(), forward())
    except (ConnectionError, asyncio.CancelledError):
        writer.close()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", type=int, default=9201)
    parser.add_argument("--target", type=int, default=9200)
    parser.add_argument("--delay-ms", type=float, default=25.0)
    args = parser.parse_args()
    delay = args.delay_ms / 1000

    async def handle(client_reader, client_writer):
        server_reader, server_writer = await asyncio.open_connection(
            "127.0.0.1", args.target)
        await asyncio.gather(
            pipe(client_reader, server_writer, delay),
            pipe(server_reader, client_writer, delay),
            return_exceptions=True)

    server = await asyncio.start_server(handle, "127.0.0.1", args.listen)
    print(f"Delay proxy on localhost:{args.listen} -> localhost:{args.target}, "
          f"{args.delay_ms:g} ms each way", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
