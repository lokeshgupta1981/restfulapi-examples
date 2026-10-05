"""Send POST and PUT to /lab/<code> with requests and print what reached /echo."""
import requests

BASE = "http://127.0.0.1:9190"
ORDER = '{"sku": "BOOK-42", "qty": 2}'
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer demo-token"}

for method in ("POST", "PUT"):
    for code in (301, 302, 303, 307, 308):
        response = requests.request(method, f"{BASE}/lab/{code}", data=ORDER, headers=HEADERS, timeout=5)
        print(f"{method:4} {code} -> {response.json()['summary']}")

response = requests.post(f"{BASE}/lab/308?cross=1", data=ORDER, headers=HEADERS, timeout=5)
print(f"POST 308 to another host -> {response.json()['summary']}")
