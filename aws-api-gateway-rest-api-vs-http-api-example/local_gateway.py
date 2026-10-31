"""A tiny local stand-in for the two API Gateway front doors. It is NOT API Gateway.

It turns a real HTTP request into the Lambda event that each API type sends,
calls the handler in-process, and turns the handler's return value back into
an HTTP response, following the rules in the API Gateway developer guide:

  /rest/prod/...  -> payload format 1.0 (REST API, Lambda proxy integration).
                     The function must return statusCode/headers/body,
                     otherwise the client gets 502 Bad Gateway.
  /http/...       -> payload format 2.0 (HTTP API). If the function returns
                     JSON without statusCode, the client gets 200 with
                     content-type application/json.

It does no authorization, throttling or validation. It only fills in a demo
caller identity so the handler can show where each format puts it.
Run: PORT=8000 python local_gateway.py
"""

import base64
import json
import os
import re
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
import handler as orders  # noqa: E402

ROUTES = [  # (method, resource template, function)
    ("GET", "/orders/{orderId}", orders.handler),
    ("POST", "/orders", orders.handler),
    ("GET", "/health", lambda event, context: {"status": "ok"}),  # returns plain JSON on purpose
]


def match(method, path):
    for verb, template, fn in ROUTES:
        pattern = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", template) + "$"
        m = re.match(pattern, path)
        if verb == method and m:
            return template, m.groupdict() or None, fn
    return None, None, None


def v1_event(method, path, resource, params, query, headers, body):
    return {
        "resource": resource, "path": path, "httpMethod": method,
        "headers": {k: v[-1] for k, v in headers.items()},
        "multiValueHeaders": headers,
        "queryStringParameters": {k: v[-1] for k, v in query.items()} or None,
        "multiValueQueryStringParameters": query or None,
        "pathParameters": params, "stageVariables": None,
        "requestContext": {
            "resourcePath": resource, "httpMethod": method, "path": "/prod" + path,
            "stage": "prod", "requestId": str(uuid.uuid4()),
            "identity": {"apiKeyId": "demo-key-id" if "x-api-key" in headers else None},
        },
        "body": body, "isBase64Encoded": False,
    }


def v2_event(method, path, resource, params, raw_query, query, headers, body):
    ctx = {
        "http": {"method": method, "path": path, "protocol": "HTTP/1.1"},
        "routeKey": f"{method} {resource}", "stage": "$default",
        "requestId": str(uuid.uuid4()), "timeEpoch": int(time.time() * 1000),
    }
    if "authorization" in headers:
        ctx["authorizer"] = {"jwt": {"claims": {"sub": "demo-user"}, "scopes": None}}
    return {
        "version": "2.0", "routeKey": f"{method} {resource}",
        "rawPath": path, "rawQueryString": raw_query,
        "headers": {k: ",".join(v) for k, v in headers.items()},
        "queryStringParameters": {k: ",".join(v) for k, v in query.items()} or None,
        "pathParameters": params, "requestContext": ctx,
        "body": body, "isBase64Encoded": False,
    }


def v1_response(result):
    ok = isinstance(result, dict) and isinstance(result.get("statusCode"), int) \
        and isinstance(result.get("body", ""), str)
    if not ok:
        return 502, {"Content-Type": "application/json"}, \
            json.dumps({"message": "local stand-in: malformed Lambda proxy response"})
    return result["statusCode"], result.get("headers", {}), result.get("body", "")


def v2_response(result):
    if isinstance(result, dict) and "statusCode" in result:
        body = result.get("body", "")
        if result.get("isBase64Encoded"):
            body = base64.b64decode(body).decode()
        return result["statusCode"], result.get("headers", {}), body
    body = result if isinstance(result, str) else json.dumps(result)
    return 200, {"content-type": "application/json"}, body


class Gateway(BaseHTTPRequestHandler):
    def handle_any(self):
        url = urlsplit(self.path)
        if url.path.startswith("/rest/prod/"):
            api, path = "rest", url.path[len("/rest/prod"):]
        elif url.path.startswith("/http/"):
            api, path = "http", url.path[len("/http"):]
        else:
            return self.send(404, {"Content-Type": "application/json"}, '{"message":"Not Found"}')

        resource, params, fn = match(self.command, path)
        if fn is None:
            return self.send(404, {"Content-Type": "application/json"}, '{"message":"Not Found"}')

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else None
        headers = {}
        for k, v in self.headers.items():
            headers.setdefault(k.lower(), []).append(v)
        query = parse_qs(url.query)

        if api == "rest":
            event = v1_event(self.command, path, resource, params, query, headers, body)
            status, out_headers, out_body = v1_response(fn(event, None))
        else:
            event = v2_event(self.command, path, resource, params, url.query, query, headers, body)
            status, out_headers, out_body = v2_response(fn(event, None))
        self.send(status, out_headers, out_body)

    do_GET = do_POST = handle_any

    def send(self, status, headers, body):
        data = body.encode()
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"local stand-in listening on http://127.0.0.1:{port} (/rest/prod/... and /http/...)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Gateway).serve_forever()
