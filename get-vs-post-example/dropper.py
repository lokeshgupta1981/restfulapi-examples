"""A broken upstream: reads the request, then closes the connection without a response.

Run: python dropper.py   (listens on 127.0.0.1:9122)
"""
import socket

with socket.create_server(("127.0.0.1", 9122)) as server:
    print("dropper listening on 127.0.0.1:9122", flush=True)
    while True:
        conn, _ = server.accept()
        with conn:
            request_head = conn.recv(65536).split(b"\r\n", 1)[0]
            print("dropped:", request_head.decode(), flush=True)
