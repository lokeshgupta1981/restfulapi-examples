"""Two origins on one machine: a page on port 9310 and an Orders API on port 9311.

The API logs every request it gets, so we can see which fetch() calls
trigger a CORS preflight (OPTIONS) request.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PAGE_ORIGIN = "http://127.0.0.1:9310"

PAGE = b"""<!doctype html>
<meta charset="utf-8">
<title>CORS and Content-Type</title>
<script>
async function send(path, contentType) {
  try {
    const res = await fetch('http://127.0.0.1:9311' + path, {
      method: 'POST',
      headers: { 'Content-Type': contentType },
      body: JSON.stringify({ item: 'keyboard', quantity: 2 }),
    });
    return path + ' ' + contentType + ' -> HTTP ' + res.status;
  } catch (err) {
    return path + ' ' + contentType + ' -> ' + err.name + ': ' + err.message;
  }
}
</script>
"""


class PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


class ApiHandler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        print(f"API got {self.command} {self.path} "
              f"(Content-Type: {self.headers.get('Content-Type')}, "
              f"Access-Control-Request-Headers: {self.headers.get('Access-Control-Request-Headers')}) "
              f"-> {code}", flush=True)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", PAGE_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST")
        # /orders allows the Content-Type header; /legacy-orders does not.
        if self.path == "/orders":
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        payload = json.dumps({"id": 1001}).encode("utf-8")
        self.send_response(201)
        self.send_header("Access-Control-Allow-Origin", PAGE_ORIGIN)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(port, handler):
    HTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=serve, args=(9310, PageHandler), daemon=True).start()
    print("Page on http://127.0.0.1:9310, API on http://127.0.0.1:9311", flush=True)
    serve(9311, ApiHandler)
