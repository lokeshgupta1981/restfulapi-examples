"""Echo server: prints the Content-Type and Accept headers that each client sends."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT", "9300"))


class EchoHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        result = {
            "client": self.headers.get("X-Client", "?"),
            "contentType": self.headers.get("Content-Type"),
            "accept": self.headers.get("Accept"),
            "body": body,
        }
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        # Simulates a proxy error page: HTML where the client expects JSON.
        page = b"<html><body><h1>502 Bad Gateway</h1></body></html>"
        self.send_response(502)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Echo server on http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), EchoHandler).serve_forever()
