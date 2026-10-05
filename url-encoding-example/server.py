"""Document API that shows how a server decodes the path and the query string.

GET /v2/docs/{name}?tag=...  decodes once, after splitting (correct)
GET /v1/docs/{name}          decodes the path a second time (the double-decode bug)
GET /v1/admin/stats, /v2/admin/stats  blocked by an access check for /admin
POST /v2/notes  reads an application/x-www-form-urlencoded body
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, unquote

PORT = int(os.environ.get("PORT", "9160"))
BAD_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def decode_strict(text):
    """Decode percent-escapes as UTF-8 and fail on malformed input."""
    if BAD_ESCAPE.search(text):
        raise ValueError("malformed percent-escape")
    return unquote(text, encoding="utf-8", errors="strict")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        raw_path, _, raw_query = self.path.partition("?")
        try:
            # Split on "/" first, then decode each segment (RFC 3986 section 2.4).
            segments = [decode_strict(s) for s in raw_path.split("/")[1:]]
            if BAD_ESCAPE.search(raw_query):
                raise ValueError("malformed percent-escape in query")
            query = {}
            for key, value in parse_qsl(raw_query, keep_blank_values=True,
                                        encoding="utf-8", errors="strict"):
                query.setdefault(key, []).append(value)
        except (ValueError, UnicodeDecodeError) as err:
            return self.send_json(400, {"error": "bad percent-encoding",
                                        "detail": str(err),
                                        "raw_target": self.path})

        # Access check: runs on the path decoded once.
        if len(segments) >= 2 and segments[1] == "admin":
            return self.send_json(403, {"error": "admin area is blocked"})

        if segments[:1] == ["v1"]:
            # Bug: the router decodes values that were already decoded.
            segments = [unquote(s) for s in segments]

        if len(segments) == 3 and segments[1] == "docs":
            return self.send_json(200, {"raw_target": self.path,
                                        "name": segments[2],
                                        "query": query})
        if len(segments) == 3 and segments[1] == "admin" and segments[2] == "stats":
            return self.send_json(200, {"admin": True, "users": 42})
        return self.send_json(404, {"error": "not found", "segments": segments})

    def do_POST(self):
        # Form body: same encoding rules as a query string (+ is a space).
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("ascii", errors="replace")
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("application/x-www-form-urlencoded"):
            return self.send_json(415, {"error": "send application/x-www-form-urlencoded"})
        fields = dict(parse_qsl(raw_body, keep_blank_values=True, encoding="utf-8"))
        return self.send_json(201, {"raw_body": raw_body, "fields": fields})


if __name__ == "__main__":
    print(f"Listening on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
