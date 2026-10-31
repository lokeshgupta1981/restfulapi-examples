"""How Python encodes the same values, and what the server receives."""
import json
from urllib.parse import quote, quote_plus, unquote, urlencode

import requests

BASE = "http://127.0.0.1:9160"
# "caf\u00e9" is "cafe" with an accented e (U+00E9), a non-ASCII character.
VALUES = ["C++ & Java/Go", "caf\u00e9", "50% off", "~user*(1)!"]


def show(text):
    """Print a string in quotes, with non-ASCII characters as \\uXXXX."""
    return json.dumps(text)


for title, encode in [("quote(v)", quote),
                      ("quote(v, safe='')", lambda v: quote(v, safe="")),
                      ("quote_plus(v)", quote_plus),
                      ("urlencode({'q': v})", lambda v: urlencode({"q": v}))]:
    print(title + ":")
    for v in VALUES:
        print(f"  {show(v):18} -> {encode(v)}")

print()
print("hand-built URL (no encoding):")
response = requests.get(f"{BASE}/v2/docs/report?tag=C++ & Java/Go")
print("  sent:    ", response.request.path_url)
print("  status:  ", response.status_code)
print("  received:", json.dumps(response.json()["query"]))

print("requests with params=")
response = requests.get(f"{BASE}/v2/docs/report", params={"tag": "C++ & Java/Go"})
print("  sent:    ", response.request.path_url)
print("  received:", json.dumps(response.json()["query"]))

print("path segment from quote(v) with the default safe='/':")
doc_name = "AB/12 caf\u00e9"
response = requests.get(f"{BASE}/v2/docs/{quote(doc_name)}")
print("  sent:    ", response.request.path_url)
print("  status:  ", response.status_code)

print("path segment from quote(v, safe=''):")
response = requests.get(f"{BASE}/v2/docs/{quote(doc_name, safe='')}")
print("  sent:    ", response.request.path_url)
print("  received:", show(response.json()["name"]))

print()
print("double encoding:")
once = quote("caf\u00e9", safe="")
twice = quote(once, safe="")
print("  encoded once: ", once)
print("  encoded twice:", twice)
response = requests.get(f"{BASE}/v2/docs/{twice}")
print("  server name:  ", show(response.json()["name"]))
print("  params= with an already encoded value:")
response = requests.get(f"{BASE}/v2/docs/report", params={"tag": quote_plus("C++")})
print("    sent:    ", response.request.path_url)
print("    received:", json.dumps(response.json()["query"]))
