"""Reads the HTTP 302 instead of following it."""
import requests

payment_response = requests.post(
    "http://127.0.0.1:9182/redirect/302",
    json={"amount": "49.90"},
    allow_redirects=False,
    timeout=5,
)
print("requests:", payment_response.status_code, payment_response.headers["Location"])
