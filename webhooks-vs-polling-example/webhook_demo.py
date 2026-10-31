"""Sends four webhook requests to receiver.py and prints how it answers.

1. a correctly signed event                  -> HTTP 204, processed
2. the same event again (a retry)            -> HTTP 204, dropped as a duplicate
3. the same signature with a changed body    -> HTTP 401
4. a correctly signed event, 10 minutes old  -> HTTP 401 (replay protection)

Standard library only. Uses port 9143.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from provider import sign

HERE = Path(__file__).parent
SECRET = "whsec_demo_secret"   # demo value only
URL = "http://127.0.0.1:9143/webhooks/orders"


def post(body, headers):
    request = urllib.request.Request(URL, data=body, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def signed_headers(event_id, timestamp, body):
    return {"webhook-id": event_id,
            "webhook-timestamp": str(timestamp),
            "webhook-signature": sign(SECRET, event_id, str(timestamp), body)}


def main():
    (HERE / "results").mkdir(exist_ok=True)
    out = HERE / "results" / "webhook-demo.json"
    receiver = subprocess.Popen([sys.executable, "receiver.py", "--port", "9143", "--duration", "4",
                                 "--out", str(out)], cwd=HERE)
    time.sleep (1)

    event = {"id": "evt_0042", "seq": 42, "type": "order.status_changed",
             "created_at": "2026-10-31T10:00:00.000Z", "created_ts": time.time(),
             "data": {"order_id": "ord_1004", "status": "shipped"}}
    body = json.dumps(event).encode()
    now = int(time.time())
    headers = signed_headers(event["id"], now, body)

    print("1. signed event:          ", post(body, headers), flush=True)
    time.sleep (0.3)
    print("2. same event again:      ", post(body, headers), flush=True)

    forged = body.replace(b'"shipped"', b'"refunded"')
    print("3. body changed:          ", post(forged, headers), flush=True)

    old = now - 600
    print("4. signed 10 minutes ago: ", post(body, signed_headers(event["id"], old, body)), flush=True)

    receiver.wait()
    result = json.loads(out.read_text())
    print(f"processed: {result['events_seen']}, duplicates dropped: {result['duplicates']}")


if __name__ == "__main__":
    main()
