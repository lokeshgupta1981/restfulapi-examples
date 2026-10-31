"""Sends one GET and one POST over a plain socket and prints the bytes in both directions.

Needs the app on port 9120 (./start.sh). Run: python wire.py
"""
import json
import socket

HOST, PORT = "localhost", 9120


def exchange(raw_request):
    with socket.create_connection((HOST, PORT)) as conn:
        conn.sendall(raw_request.encode())
        response = b""
        while chunk := conn.recv(65536):
            response += chunk
    print("--- request sent ---")
    print(raw_request.replace("\r\n", "\n"))
    print("--- response received ---")
    print(response.decode().replace("\r\n", "\n"))
    print()


# GET: the input is in the URL (path and query string), there is no body.
exchange(
    "GET /orders?status=paid HTTP/1.1\r\n"
    f"Host: {HOST}:{PORT}\r\n"
    "Connection: close\r\n"
    "\r\n"
)

# POST: the input is in the body, described by Content-Type and Content-Length.
body = json.dumps({"customer_email": "kim@example.com", "total": 30})
exchange(
    "POST /orders HTTP/1.1\r\n"
    f"Host: {HOST}:{PORT}\r\n"
    "Content-Type: application/json\r\n"
    f"Content-Length: {len(body)}\r\n"
    "Connection: close\r\n"
    "\r\n"
    + body
)
