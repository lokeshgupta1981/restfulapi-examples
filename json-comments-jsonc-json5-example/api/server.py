"""A small orders API that shows why comments do not belong in API traffic.

POST /orders            strict JSON body; a comment gives HTTP 400 (Problem Details)
GET  /orders/42         a correct JSON response
GET  /legacy/orders/42  a wrong response: JSON with a comment, sent as application/json
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "9185"))
ORDER = {"id": 42, "status": "PAID", "total": 59.90}


class OrdersHandler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type="application/json"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/orders/42":
            self.send_body(200, json.dumps(ORDER))
        elif self.path == "/legacy/orders/42":
            # Wrong on purpose: RFC 8259 section 10 says a generator MUST produce strict JSON.
            body = '{\n  // total includes tax\n  "id": 42, "status": "PAID", "total": 59.90\n}'
            self.send_body(200, body)
        else:
            self.send_body(404, json.dumps({"title": "Not Found", "status": 404}),
                           "application/problem+json")

    def do_POST(self):
        if self.path != "/orders":
            self.send_body(404, json.dumps({"title": "Not Found", "status": 404}),
                           "application/problem+json")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            order = json.loads(raw)
        except json.JSONDecodeError as error:
            problem = {
                "type": "https://example.com/problems/invalid-json",
                "title": "Request body is not valid JSON",
                "status": 400,
                "detail": f"{error.msg} at line {error.lineno}, column {error.colno}",
            }
            self.send_body(400, json.dumps(problem, indent=2), "application/problem+json")
            return
        created = {"id": 43, "status": "NEW", "items": order.get("items", [])}
        self.send_body(201, json.dumps(created))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print(f"Orders API on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), OrdersHandler).serve_forever()
