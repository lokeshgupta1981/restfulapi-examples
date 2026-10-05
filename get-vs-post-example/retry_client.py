"""A requests session with automatic retries on HTTP 503."""
import json
import urllib.request

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "http://localhost:9120"

retry = Retry(total=2, status_forcelist=[503], backoff_factor=0, raise_on_status=False)
session = requests.Session()
session.mount("http://", HTTPAdapter(max_retries=retry))

print("retried methods:", sorted(Retry.DEFAULT_ALLOWED_METHODS))

get_response = session.get(f"{API}/unstable")
print("GET  /unstable ->", get_response.status_code)

post_response = session.post(f"{API}/unstable", json={"total": 10})
print("POST /unstable ->", post_response.status_code)

with urllib.request.urlopen(f"{API}/stats") as response:
    stats = json.load(response)
print("attempts that reached the app:",
      {key: value for key, value in stats.items() if key.endswith("/unstable")})
