"""Client that changes one field with PUT and If-Match, and re-reads the
ticket when another client changed it first (HTTP 412).

Run with the server on port 9110:  python client.py
Uses only the Python standard library.
"""
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("BASE", "http://localhost:9110")
TICKET_URL = f"{BASE}/tickets/TCK-1001"


def send(method, url, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("ETag"), json.loads(response.read())
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("ETag"), json.loads(err.read())


def set_priority(priority, before_write=None, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        status, etag, ticket = send("GET", TICKET_URL)
        print(f"attempt {attempt}: GET -> {status}, ETag {etag}")
        ticket["priority"] = priority
        if before_write:
            before_write()      # another client writes between our GET and PUT
            before_write = None
        headers = {"Content-Type": "application/json", "If-Match": etag}
        status, new_etag, body = send("PUT", TICKET_URL, ticket, headers)
        print(f"attempt {attempt}: PUT If-Match {etag} -> {status}")
        if status != 412:
            return status, new_etag, body
    raise RuntimeError("The ticket kept changing; giving up.")


def other_client_closes_ticket():
    patch_headers = {"Content-Type": "application/merge-patch+json"}
    status, etag, _ = send("PATCH", TICKET_URL, {"status": "closed"}, patch_headers)
    print(f"other client: PATCH status=closed -> {status}, ETag {etag}")


status, etag, ticket = set_priority("high", before_write=other_client_closes_ticket)
print(f"final: {status}, ETag {etag}")
print(json.dumps(ticket))
