"""Python requests: two challenge lines, and HTTPBasicAuth for the legacy endpoint.

The password is a fake demo value.
"""
import requests
from requests.auth import HTTPBasicAuth

API = "http://127.0.0.1:9420"

# requests joins repeated header lines with ", " just like fetch().
v2_response = requests.get(API + "/v2/shipments")
print("GET /v2/shipments ->", v2_response.status_code)
print("  WWW-Authenticate:", v2_response.headers["WWW-Authenticate"])

# Without credentials the server sends a Basic challenge.
legacy_response = requests.get(API + "/legacy/reports")
print("GET /legacy/reports ->", legacy_response.status_code)
print("  WWW-Authenticate:", legacy_response.headers["WWW-Authenticate"])

# HTTPBasicAuth builds "Authorization: Basic base64(user:password)" for every request.
auth = HTTPBasicAuth("ana", "demo-pass-123")
authed_response = requests.get(API + "/legacy/reports", auth=auth)
print("GET /legacy/reports with HTTPBasicAuth ->", authed_response.status_code)
print("  Authorization sent:", authed_response.request.headers["Authorization"])
print("  body:", authed_response.json())

# Credentials in the URL: requests moves them into an Authorization: Basic header.
url_response = requests.get("http://ana:demo-pass-123@127.0.0.1:9420/legacy/reports")
print("GET with user:password in the URL ->", url_response.status_code)
