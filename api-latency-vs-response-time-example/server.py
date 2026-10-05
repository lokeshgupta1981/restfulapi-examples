"""Orders API that reports its own processing time in a Server-Timing header.

GET /orders/{id}   one order; most lookups take about 10 ms, a few hit a slow
                   path (a simulated lock wait of 300 to 600 ms)
GET /orders/export all orders as JSON lines, sent in 20 pages; the first page
                   goes out early, so time to first byte is short and the
                   total response time is long

Run: python3 server.py [--port 9200] [--tls] [--keep-nagle]
"""
import argparse
import json
import random
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Fixed seed, so every run of the demo sees the same pattern of slow requests.
rng = random.Random(42)
rng_lock = threading.Lock()


def simulated_db_seconds():
    """Time the order lookup takes: 8-12 ms, and 300-600 ms for 3% of calls."""
    with rng_lock:
        if rng.random() < 0.03:
            return rng.uniform(0.300, 0.600)
        return rng.uniform(0.008, 0.012)


class OrdersHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive, so clients can reuse a connection
    disable_nagle_algorithm = True  # send small responses without waiting for an ACK

    def do_GET(self):
        if self.path.startswith("/orders/export"):
            self.send_export()
        elif self.path.startswith("/orders/"):
            self.send_order(self.path.rsplit("/", 1)[-1])
        else:
            self.send_error(404)

    def send_order(self, order_id):
        start = time.perf_counter()

        db_seconds = simulated_db_seconds()
        time.sleep (db_seconds)  # stands in for the database query
        db_ms = (time.perf_counter() - start) * 1000

        app_start = time.perf_counter()
        order = {"id": order_id, "status": "SHIPPED", "total": "149.90",
                 "currency": "EUR", "items": [{"sku": "BK-101", "qty": 2}]}
        body = json.dumps(order).encode()
        app_ms = (time.perf_counter() - app_start) * 1000
        total_ms = (time.perf_counter() - start) * 1000

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Server-Timing",
            f"db;dur={db_ms:.1f}, app;dur={app_ms:.1f}, total;dur={total_ms:.1f}")
        self.end_headers()
        self.wfile.write(body)

    def send_export(self):
        start = time.perf_counter()
        time.sleep (0.015)  # first page from the database
        first_page_ms = (time.perf_counter() - start) * 1000

        self.send_response(200)
        self.send_header("Content-Type", "application/jsonl")
        self.send_header("Transfer-Encoding", "chunked")
        # The header goes out before the body, so it can only report the
        # time spent before the first byte.
        self.send_header("Server-Timing", f"db-first-page;dur={first_page_ms:.1f}")
        self.end_headers()

        line = json.dumps({"id": 0, "status": "SHIPPED", "total": "149.90",
                           "note": "x" * 900}) + "\n"
        for page in range(20):
            if page > 0:
                time.sleep (0.015)  # next page from the database
            chunk = (line * 500).encode()  # about 470 KB per page
            self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
        self.wfile.write(b"0\r\n\r\n")

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet during load runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9200)
    parser.add_argument("--tls", action="store_true",
                        help="serve HTTPS with cert.pem and key.pem")
    parser.add_argument("--keep-nagle", action="store_true",
                        help="leave Nagle's algorithm on to see the 40 ms gap")
    args = parser.parse_args()
    if args.keep_nagle:
        OrdersHandler.disable_nagle_algorithm = False

    server = ThreadingHTTPServer(("127.0.0.1", args.port), OrdersHandler)
    scheme = "http"
    if args.tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("cert.pem", "key.pem")
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    print(f"Orders API on {scheme}://localhost:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
