"""Which bytes end up in a Basic header when the password is not ASCII."""
import base64

import requests

PASSWORD = "demo-café-123"  # demo value with one non-ASCII character

prepared = requests.Request("GET", "http://127.0.0.1:9771/echo",
                            auth=("reports-app", PASSWORD)).prepare()
requests_value = prepared.headers["Authorization"]
print("requests sends    ", requests_value)
print("decoded bytes     ", base64.b64decode(requests_value.split(" ", 1)[1]))

utf8_value = "Basic " + base64.b64encode(f"reports-app:{PASSWORD}".encode("utf-8")).decode("ascii")
print("UTF-8 by hand     ", utf8_value)
print("decoded bytes     ", base64.b64decode(utf8_value.split(" ", 1)[1]))

# Fix: pass bytes, and requests uses them as they are.
prepared = requests.Request("GET", "http://127.0.0.1:9771/echo",
                            auth=(b"reports-app", PASSWORD.encode("utf-8"))).prepare()
print("requests with bytes", prepared.headers["Authorization"])
