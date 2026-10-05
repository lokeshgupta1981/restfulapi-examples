import requests

response = requests.post(
    "http://127.0.0.1:9207/orders/bulk-cancel",
    json={"items": [{"orderId": "ord-1001"}, {"orderId": "ord-1002"}]},
    timeout=5,
)
response.raise_for_status()  # does not raise for HTTP 207
print("status:", response.status_code, "ok:", response.ok)

results = response.json()["results"]
failed_items = [result for result in results if result["status"] >= 300]
print("failed order ids:", [result["orderId"] for result in failed_items])
