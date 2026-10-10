"""stdio binding: one JSON-RPC message per line on stdin and stdout.

The client starts this file as a subprocess. Logs go to stderr, never to stdout.
"""

import json
import sys

from core import handle

print("orders-demo stdio server started", file=sys.stderr, flush=True)
for line in sys.stdin:  # ends when the client closes stdin, which is the shutdown signal
    line = line.strip()
    if not line:
        continue
    message = json.loads(line)
    if "id" not in message:  # a notification, such as notifications/cancelled
        continue
    for reply in handle(message):
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()
print("stdin closed, exiting", file=sys.stderr, flush=True)
