"""Sends POST, PUT and DELETE to a 302, 303 or 307 redirect and prints the method
that reached /echo after the client followed the redirect."""
import sys

import httpx
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9182"
BODY = {"amount": "49.90"}


def with_requests(method, code):
    response = requests.request(method, f"{BASE_URL}/redirect/{code}", json=BODY, timeout=5)
    return response.json()


def with_httpx(method, code):
    with httpx.Client(follow_redirects=True, timeout=5) as client:
        response = client.request(method, f"{BASE_URL}/redirect/{code}", json=BODY)
    return response.json()


def describe(echo):
    return f"{echo['method']} body={echo['body_bytes']}"


print(f"requests {requests.__version__}, httpx {httpx.__version__}")
print(f"{'sent':<8}{'status':<8}{'requests':<20}{'httpx':<20}")
for code in (302, 303, 307):
    for method in ("POST", "PUT", "DELETE"):
        print(f"{method:<8}{code:<8}{describe(with_requests(method, code)):<20}"
              f"{describe(with_httpx(method, code)):<20}")

# Authorization header after a 302 to another host (127.0.0.1 -> localhost)
other_host = f"{BASE_URL}/redirect/302?to=http://localhost:9182/echo"
token_header = {"Authorization": "Bearer demo-token"}
same = requests.get(f"{BASE_URL}/redirect/302", headers=token_header, timeout=5).json()
cross = requests.get(other_host, headers=token_header, timeout=5).json()
print(f"requests Authorization kept: same host={same['authorization']}, other host={cross['authorization']}")
with httpx.Client(follow_redirects=True, timeout=5) as client:
    same = client.get(f"{BASE_URL}/redirect/302", headers=token_header).json()
    cross = client.get(other_host, headers=token_header).json()
print(f"httpx Authorization kept: same host={same['authorization']}, other host={cross['authorization']}")
