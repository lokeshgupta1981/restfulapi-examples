"""Prints every HTTP request exactly as it arrives on the socket.

Run: python3 wire_server.py   (listens on 127.0.0.1:9170, change with PORT=...)

GET /form serves an HTML page with three forms (one per enctype), so a
browser can submit the same ticket in each format. Every other request
gets a small JSON reply, and its raw bytes are printed to stdout.
Bytes outside printable ASCII are shown as \\xNN.
"""
import os
import socket
import threading

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "9170"))

FORM_PAGE = b"""<!doctype html>
<html><body>
<form id="urlencoded" method="post" action="/tickets">
  <input name="subject" value="Login fails &amp; shows 500">
  <input name="priority" value="high">
  <input name="tags" value="auth"><input name="tags" value="web">
  <button>Send</button>
</form>
<form id="multipart" method="post" action="/tickets" enctype="multipart/form-data">
  <input name="subject" value="Login fails &amp; shows 500">
  <input name="priority" value="high">
  <input type="file" name="attachment">
  <button>Send</button>
</form>
<form id="plain" method="post" action="/tickets" enctype="text/plain">
  <input name="subject" value="Login fails &amp; shows 500">
  <input name="priority" value="high">
  <button>Send</button>
</form>
</body></html>
"""

print_lock = threading.Lock()


def show(raw):
    """Return the raw bytes as text: CRLF visible, other control bytes escaped."""
    out = []
    for b in raw:
        if b == 0x0D:
            continue
        if b == 0x0A or 0x20 <= b < 0x7F:
            out.append(chr(b))
        else:
            out.append("\\x%02x" % b)
    return "".join(out)


def read_request(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(65536)
        if not chunk:
            return None
        data += chunk
    head, _, body = data.partition(b"\r\n\r\n")
    headers = {}
    for line in head.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        headers[name.strip().lower()] = value.strip()
    if b"content-length" in headers:
        length = int(headers[b"content-length"])
        while len(body) < length:
            chunk = conn.recv(65536)
            if not chunk:
                break
            body += chunk
    elif headers.get(b"transfer-encoding", b"").lower() == b"chunked":
        while not body.endswith(b"0\r\n\r\n"):
            chunk = conn.recv(65536)
            if not chunk:
                break
            body += chunk
    return head, body


def handle(conn):
    with conn:
        result = read_request(conn)
        if result is None:
            return
        head, body = result
        request_line = head.split(b"\r\n")[0]
        if request_line.startswith(b"GET /form"):
            reply = FORM_PAGE
            ctype = b"text/html; charset=utf-8"
        else:
            reply = b'{"received": true}'
            ctype = b"application/json"
            with print_lock:
                print("----- request (%d body bytes) -----" % len(body))
                print(show(head + b"\r\n\r\n" + body))
                print("----- end -----", flush=True)
        conn.sendall(
            b"HTTP/1.1 200 OK\r\nContent-Type: " + ctype
            + b"\r\nContent-Length: " + str(len(reply)).encode()
            + b"\r\nConnection: close\r\n\r\n" + reply
        )


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"wire server on http://{HOST}:{PORT}", flush=True)
        while True:
            conn, _ = server.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
