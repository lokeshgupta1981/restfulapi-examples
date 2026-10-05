"""Orders API that publishes order events two ways.

1. A change feed for polling clients:  GET /events?after=<seq>
   The response carries an ETag, so a client can send If-None-Match
   and get HTTP 304 when nothing changed.
2. Webhooks: every event is POSTed, signed with HMAC-SHA256, to the
   subscriber URL. Failed deliveries are retried on a short schedule,
   then given up (dead-lettered).

Standard library only (Python 3.13).
"""
import argparse
import base64
import hashlib
import hmac
import json
import random
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATUSES = ["paid", "packed", "shipped", "delivered"]

lock = threading.Lock()
events = []          # the change feed, oldest first
stats = {
    "feed_requests": 0,
    "feed_200": 0,
    "feed_304": 0,
    "feed_200_empty": 0,
    "webhook_attempts": 0,
    "webhook_delivered": 0,
    "webhook_dead_lettered": 0,
}
dead_letter = []


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sign(secret, msg_id, timestamp, body):
    """Signature over '<id>.<timestamp>.<body>', in the Standard Webhooks format."""
    signed = f"{msg_id}.{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def deliver(event, url, secret, retry_delays):
    """POST one event; retry after each delay in retry_delays, then give up.

    This sender uses its own fixed schedule and ignores Retry-After.
    """
    body = json.dumps(event).encode()
    attempts = [0] + retry_delays
    for number, delay in enumerate(attempts, start=1):
        time.sleep (delay)
        timestamp = str(int(time.time()))
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "webhook-id": event["id"],
                "webhook-timestamp": timestamp,
                "webhook-signature": sign(secret, event["id"], timestamp, body),
            },
        )
        with lock:
            stats["webhook_attempts"] += 1
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        except OSError:
            status = None  # connection refused or timeout
        print(f"[provider] deliver {event['id']} attempt {number} -> {status}", flush=True)
        if status is not None and 200 <= status < 300:
            with lock:
                stats["webhook_delivered"] += 1
            return
    with lock:
        stats["webhook_dead_lettered"] += 1
        dead_letter.append(event["id"])
    print(f"[provider] gave up on {event['id']} after {len(attempts)} attempts", flush=True)


def generate_events(count, mean_gap, seed, url, secret, retry_delays):
    rng = random.Random(seed)
    time.sleep (2)  # let the clients start
    for seq in range(1, count + 1):
        time.sleep (rng.expovariate(1 / mean_gap))
        order_id = f"ord_{rng.randint(1000, 1019)}"
        event = {
            "id": f"evt_{seq:04d}",
            "seq": seq,
            "type": "order.status_changed",
            "created_at": iso_now(),
            "created_ts": time.time(),
            "data": {"order_id": order_id, "status": rng.choice(STATUSES)},
        }
        with lock:
            events.append(event)
        print(f"[provider] new {event['id']} {order_id}", flush=True)
        if url:
            threading.Thread(target=deliver, args=(event, url, secret, retry_delays), daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/stats":
            with lock:
                self.send_json(200, {**stats, "events": len(events), "dead_letter": dead_letter})
            return
        if url.path != "/events":
            self.send_json(404, {"title": "Not Found"})
            return
        after = int(parse_qs(url.query).get("after", ["0"])[0])
        with lock:
            stats["feed_requests"] += 1
            last_seq = events[-1]["seq"] if events else 0
            page = [e for e in events if e["seq"] > after][:100]
        # Convention of this server: one version label for the whole feed (the newest
        # seq). The answer for any ?after=N changes only when a new event arrives,
        # so the same ETag is valid for every after value.
        etag = f'"feed-{last_seq}"'
        headers = {"ETag": etag, "Cache-Control": "no-cache"}
        if self.headers.get("If-None-Match") == etag:
            with lock:
                stats["feed_304"] += 1
            self.send_response(304)
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            return
        with lock:
            stats["feed_200"] += 1
            if not page:
                stats["feed_200_empty"] += 1
        next_after = page[-1]["seq"] if page else after
        self.send_json(200, {"events": page, "next_after": next_after}, headers)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9140)
    parser.add_argument("--events", type=int, default=30)
    parser.add_argument("--mean-gap", type=float, default=2.0, help="average seconds between events")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--webhook-url", default="")
    parser.add_argument("--secret", default="whsec_demo_secret")
    parser.add_argument("--retry", default="1,2,4", help="retry delays in seconds")
    args = parser.parse_args()
    retry_delays = [float(x) for x in args.retry.split(",") if x]

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(
        target=generate_events,
        args=(args.events, args.mean_gap, args.seed, args.webhook_url, args.secret, retry_delays),
        daemon=True,
    ).start()
    print(f"[provider] Orders API on http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
