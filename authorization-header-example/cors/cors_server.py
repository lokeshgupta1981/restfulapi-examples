"""CORS demo: a page origin (port 9780) and an API origin (port 9781).

/orders answers the preflight with Access-Control-Allow-Headers: Authorization.
/orders-wildcard answers it with Access-Control-Allow-Headers: *.
/redirect answers HTTP 302 to http://localhost:9781/echo, a different origin,
/redirect-same answers HTTP 302 to http://127.0.0.1:9781/echo, the same origin,
/redirect-port answers HTTP 302 to http://127.0.0.1:9782/echo, another port,
and /echo returns the Authorization header it got.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE_ORIGIN = "http://127.0.0.1:9780"

PAGE = b"""<!doctype html><title>CORS demo</title><script>
async function send(path) {
  try {
    const response = await fetch('http://127.0.0.1:9781' + path, {
      headers: { Authorization: 'Bearer demo-token-123' }
    });
    return path + ' -> ' + response.status + ' ' + await response.text();
  } catch (error) {
    return path + ' -> ' + error.name + ': ' + error.message;
  }
}
</script>"""


class PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, fmt, *args):
        pass


class ApiHandler(BaseHTTPRequestHandler):
    def allow_headers(self):
        return "*" if self.path.startswith("/orders-wildcard") else "Authorization"

    def allow_origin(self):
        return "*" if self.path in ("/redirect", "/redirect-same", "/redirect-port", "/echo") else PAGE_ORIGIN

    def do_OPTIONS(self):
        print("API got OPTIONS", self.path,
              "Access-Control-Request-Headers:", self.headers.get("Access-Control-Request-Headers"),
              flush=True)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.allow_origin())
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Access-Control-Allow-Headers", self.allow_headers())
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self):
        print("API got GET", self.headers.get("Host") + self.path,
              "Authorization:", self.headers.get("Authorization"), flush=True)
        targets = {
            "/redirect": "http://localhost:9781/echo",
            "/redirect-same": "http://127.0.0.1:9781/echo",
            "/redirect-port": "http://127.0.0.1:9782/echo",
        }
        if self.path in targets:
            self.send_response(302)
            self.send_header("Location", targets[self.path])
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/echo":
            body = json.dumps({"authorization": self.headers.get("Authorization")}).encode()
        else:
            body = json.dumps({"orders": [1001, 1002]}).encode()
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", self.allow_origin())
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


page = ThreadingHTTPServer(("127.0.0.1", 9780), PageHandler)
threading.Thread(target=page.serve_forever, daemon=True).start()
other_port = ThreadingHTTPServer(("127.0.0.1", 9782), ApiHandler)
threading.Thread(target=other_port.serve_forever, daemon=True).start()
ThreadingHTTPServer(("127.0.0.1", 9781), ApiHandler).serve_forever()
