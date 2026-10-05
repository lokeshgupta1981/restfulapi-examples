"""Webhook receiver with a reconciliation poll (the hybrid pattern).

- POST /webhooks/orders: checks the signature and the timestamp, drops
  duplicates by event id, answers HTTP 204 at once and queues the event.
- A background loop reads the provider's change feed every
  --reconcile-every seconds and processes any event the webhooks missed.
- --outage START:END makes the endpoint answer HTTP 503 in that window
  (seconds after start), to simulate a deploy or a crash.
"""
import argparse
import base64
import hashlib
import hmac
import json
import queue
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

lock = threading.Lock()
seen = {}            # event id -> how we got it ("webhook" or "reconcile")
delays = {"webhook": [], "reconcile": []}
counters = {"posts": 0, "rejected_503": 0, "duplicates": 0,
            "reconcile_requests": 0, "reconcile_already_seen": 0}
work = queue.Queue()


def valid_signature(secret, headers, body, tolerance=300):
    """Rejects a timestamp more than 5 minutes off, then checks the HMAC."""
    msg_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "0")
    if abs(time.time() - int(timestamp)) > tolerance:
        return False
    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(secret.encode(), signed, hashlib.sha256).digest()).decode()
    for candidate in headers.get("webhook-signature", "").split():
        version, _, value = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(value, expected):
            return True
    return False


def record(event, source):
    """Process an event once, whichever path brings it first."""
    with lock:
        if event["id"] in seen:
            counters["duplicates" if source == "webhook" else "reconcile_already_seen"] += 1
            return False
        seen[event["id"]] = source
        delays[source].append(time.time() - event["created_ts"])
    print(f"[receiver] {source:9} {event['id']} {event['data']['order_id']} -> {event['data']['status']}", flush=True)
    return True


def worker():
    while True:
        event = work.get()
        record(event, "webhook")


def reconcile_loop(provider, every, stop_at):
    after, etag = 0, None   # a real app loads the stored cursor here
    while time.time() < stop_at:
        time.sleep (every)
        while True:
            request = urllib.request.Request(f"{provider}/events?after={after}")
            if etag:
                request.add_header("If-None-Match", etag)
            with lock:
                counters["reconcile_requests"] += 1
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    etag = response.headers.get("ETag")
                    page = json.loads(response.read())
            except urllib.error.HTTPError as error:
                if error.code == 304:
                    break
                raise
            recovered = [e for e in page["events"] if record(e, "reconcile")]
            if recovered:
                print(f"[receiver] reconcile recovered {len(recovered)} missed event(s)", flush=True)
            if page["next_after"] == after:
                break
            after = page["next_after"]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    secret = ""
    started = 0.0
    outage = (0.0, 0.0)

    def log_message(self, *args):
        pass

    def reply(self, status, headers=None):
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def simulated_outage(self):
        with lock:
            counters["posts"] += 1
            down = self.outage[0] <= time.time() - self.started < self.outage[1]
            if down:
                counters["rejected_503"] += 1
        return down

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.simulated_outage():
            self.reply(503)
            return
        if not valid_signature(self.secret, self.headers, body):
            self.reply(401)
            return
        work.put(json.loads(body))   # process later, answer now
        self.reply(204)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9141)
    parser.add_argument("--provider", default="http://127.0.0.1:9140")
    parser.add_argument("--secret", default="whsec_demo_secret")
    parser.add_argument("--reconcile-every", type=float, default=0, help="0 turns reconciliation off")
    parser.add_argument("--outage", default="0:0", help="START:END seconds after start")
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    Handler.secret = args.secret
    Handler.started = time.time()
    Handler.outage = tuple(float(x) for x in args.outage.split(":"))
    stop_at = Handler.started + args.duration

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=worker, daemon=True).start()
    if args.reconcile_every:
        threading.Thread(target=reconcile_loop, args=(args.provider, args.reconcile_every, stop_at), daemon=True).start()
    print(f"[receiver] listening on http://127.0.0.1:{args.port}/webhooks/orders", flush=True)

    time.sleep (max(0.0, stop_at - time.time()))
    server.shutdown()
    with lock:
        result = {"mode": "webhook" + (" + reconcile" if args.reconcile_every else ""),
                  **counters, "events_seen": len(seen), "delays": delays}
    with open(args.out, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
