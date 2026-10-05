"""A tiny forward proxy for plain HTTP that requires Basic proxy credentials.

It answers HTTP 407 with Proxy-Authenticate when Proxy-Authorization is missing or wrong.
The user name and password are fake demo values.
"""
import base64
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PORT = 9424
EXPECTED = "Basic " + base64.b64encode(b"proxyuser:demo-proxy-pass").decode("ascii")


class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Proxy-Authorization") != EXPECTED:
            body = b"Proxy authentication required\n"
            self.send_response(407)
            self.send_header("Proxy-Authenticate", 'Basic realm="office-proxy"')
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        target = urlsplit(self.path)
        upstream = http.client.HTTPConnection(target.hostname, target.port or 80)
        # The proxy removes Proxy-Authorization: it is meant for this hop only.
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("proxy-authorization", "proxy-connection")}
        upstream.request("GET", target.path or "/", headers=headers)
        reply = upstream.getresponse()
        data = reply.read()
        self.send_response(reply.status)
        for name, value in reply.getheaders():
            if name.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler).serve_forever()
