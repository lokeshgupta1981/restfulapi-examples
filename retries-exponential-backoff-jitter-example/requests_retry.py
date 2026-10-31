"""The same retries with requests + urllib3's built-in Retry class."""
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logging.basicConfig(format="%(relativeCreated)6.0f ms  %(message)s")
logging.getLogger("urllib3").setLevel(logging.DEBUG)

retry = Retry(
    total=4,                                  # at most 4 retries, so 5 attempts
    backoff_factor=0.5,                       # 0.5 s, 1 s, 2 s, ... between retries
    backoff_jitter=0.5,                       # plus a random 0 to 0.5 s
    backoff_max=8,                            # never wait longer than 8 s
    status_forcelist=[408, 429, 500, 502, 503, 504],
    respect_retry_after_header=True,          # the default; shown for clarity
)                                             # allowed_methods: the default idempotent set

session = requests.Session()
session.mount("http://", HTTPAdapter(max_retries=retry))
session.mount("https://", HTTPAdapter(max_retries=retry))

response = session.get("http://127.0.0.1:8000/orders/1002?fail=3", timeout=2)
print(response.status_code, response.text)
