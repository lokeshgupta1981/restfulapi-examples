"""Sends the same ticket three ways with requests. Start wire_server.py first.
Run from the example root folder (error.log is there)."""
import requests

URL = "http://127.0.0.1:9170/tickets"

form_fields = {"subject": "Login fails & shows 500", "priority": "high", "tags": ["auth", "web"]}
requests.post(URL, data=form_fields)

with open("error.log", "rb") as log_file:
    requests.post(
        URL,
        data={"subject": "Login fails & shows 500", "priority": "high"},
        files={"attachment": ("error.log", log_file, "text/plain")},
    )

ticket = {"subject": "Login fails & shows 500", "priority": "high", "tags": ["auth", "web"]}
requests.post(URL, json=ticket)

print("sent 3 requests")
