"""How Python encodes the same values with different functions."""
from urllib.parse import quote, quote_plus, urlencode, unquote

import requests

VALUES = ["C++ & Java/Go", "café", "50% off", "~user*(1)!"]
BASE = "http://127.0.0.1:9160"

print("quote(v):")
for v in VALUES:
    print(f"  {v!r:18} -> {quote(v)}")
print("quote(v, safe=''):")
for v in VALUES:
    print(f"  {v!r:18} -> {quote(v, safe='')}")
print("quote_plus(v):")
for v in VALUES:
    print(f"  {v!r:18} -> {quote_plus(v)}")
print("urlencode({'q': v}):")
for v in VALUES:
    print(f"  {v!r:18} -> {urlencode({'q': v})}")

print()
print("requests with params=")
response = requests.get(f"{BASE}/v2/docs/report", params={"tag": "C++ & Java/Go"})
print("  sent:    ", response.request.path_url)
print("  received:", response.json()["query"])

print("requests with a hand-built URL (no encoding):")
response = requests.get(f"{BASE}/v2/docs/report?tag=C++ & Java/Go")
print("  sent:    ", response.request.path_url)
print("  received:", response.json()["query"])

print("requests with a path segment from quote(safe=''):")
doc_name = "AB/12 café"
response = requests.get(f"{BASE}/v2/docs/{quote(doc_name, safe='')}")
print("  sent:    ", response.request.path_url)
print("  received:", response.json()["name"])

print()
print("double encoding:")
once = quote("café", safe="")
twice = quote(once, safe="")
print("  encoded once: ", once)
print("  encoded twice:", twice)
response = requests.get(f"{BASE}/v2/docs/{twice}")
print("  server name:  ", response.json()["name"])
print("  unquote(unquote(twice)):", unquote(unquote(twice)))
