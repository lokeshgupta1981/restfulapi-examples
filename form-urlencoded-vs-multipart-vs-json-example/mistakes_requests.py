"""Two common requests mistakes, sent to the Express server (port 9171)."""
import json

import requests

URL = "http://127.0.0.1:9171/tickets"
ticket = {"subject": "Login fails & shows 500", "priority": "high"}

# Mistake 1: data= with a JSON string sends no Content-Type header at all
response = requests.post(URL, data=json.dumps(ticket))
print("data=json.dumps():", response.request.headers.get("Content-Type"), "->", response.status_code)
print(" ", response.text)

# Mistake 2: data= with a nested dict flattens it to its keys
response = requests.post(URL, data={"subject": "Login", "customer": {"id": "c-1042", "plan": "pro"}})
print("data= nested dict:", response.request.body)
print(" ", response.text)

# Fixed: json= serializes the dict and sets Content-Type: application/json
response = requests.post(URL, json={"subject": "Login", "customer": {"id": "c-1042", "plan": "pro"}})
print("json=:", response.request.headers.get("Content-Type"), "->", response.status_code)
print(" ", response.text)
