"""Python requests: Basic auth, Bearer header and redirects."""
import requests

response = requests.get("http://127.0.0.1:9771/echo", auth=("reports-app", "demo-pass-123"))
print(response.json()["authorization"])

headers = {"Authorization": "Bearer demo-token-123"}
response = requests.get("http://127.0.0.1:9771/echo", headers=headers)
print(response.json()["authorization"])

for target in ["to-same", "to-port", "to-host"]:
    response = requests.get(f"http://127.0.0.1:9771/{target}", headers=headers)
    body = response.json()
    print(f"redirect {target:8}", body["host"], body["authorization"])
