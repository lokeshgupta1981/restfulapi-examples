"""Follow a 307 or 308 by hand: same host only, same POST, and remember a 308."""
from urllib.parse import urljoin, urlparse

import requests

orders_url = "http://127.0.0.1:9190/v1/orders"
order = {"sku": "BOOK-42", "qty": 2}

response = requests.post(orders_url, json=order, allow_redirects=False, timeout=5)
if response.status_code in (307, 308):
    new_url = urljoin(orders_url, response.headers["Location"])
    if urlparse(new_url).netloc != urlparse(orders_url).netloc:
        raise RuntimeError(f"Refusing to send the order to another host: {new_url}")
    if response.status_code == 308:
        print(f"Moved for good, update the stored URL: {orders_url} -> {new_url}")
        orders_url = new_url
    response = requests.post(new_url, json=order, allow_redirects=False, timeout=5)

print(response.status_code, response.json())
