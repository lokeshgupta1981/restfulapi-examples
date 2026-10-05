"""Echo server for the client demos.

GET /echo returns the Authorization and Proxy-Authorization lines the server
got. Used as a proxy (curl -x), it echoes the request the proxy would forward.
GET /to-same, /to-port and /to-host answer HTTP 302 and point to /echo on the
same origin, on another port, or on another host name.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9771
OTHER_PORT = 9772 if PORT == 9771 else 9771

REDIRECTS = {
    "/to-same": f"http://127.0.0.1:{PORT}/echo",
    "/to-port": f"http://127.0.0.1:{OTHER_PORT}/echo",
    "/to-host": f"http://localhost:{PORT}/echo",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in REDIRECTS:
            self.send_response(302)
            self.send_header("Location", REDIRECTS[path])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps({
            "host": self.headers.get("Host"),
            "authorization": self.headers.get_all("Authorization") or [],
            "proxy_authorization": self.headers.get_all("Proxy-Authorization") or [],
            "user_agent": self.headers.get("User-Agent"),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
