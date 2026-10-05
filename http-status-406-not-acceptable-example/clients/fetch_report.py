import sys

import requests

CLIENT_FORMATS = ["text/csv", "application/json"]  # formats this client can parse


def fetch_report(report_url: str, accept_header: str) -> requests.Response:
    response = requests.get(report_url, headers={"Accept": accept_header}, timeout=5)
    content_type = response.headers.get("Content-Type", "(none)")
    print(accept_header, "->", response.status_code, content_type)
    if response.status_code != 406:
        return response

    # A firewall page (HTML) or an empty body has no list of formats to pick from.
    if "json" not in content_type:
        raise RuntimeError("HTTP 406 without a list of formats; check the Accept default and any firewall")

    # Retrying with the same Accept gives HTTP 406 again, so we change it once.
    problem = response.json()
    offered = [entry["type"] for entry in problem.get("available", [])]
    usable = [media_type for media_type in CLIENT_FORMATS if media_type in offered]
    if not usable:
        raise RuntimeError("Server offers no format we can read: " + ", ".join(offered))

    retry_response = requests.get(report_url, headers={"Accept": usable[0]}, timeout=5)
    print(usable[0], "->", retry_response.status_code, retry_response.headers["Content-Type"])
    return retry_response


report_url = sys.argv[1]
try:
    report_response = fetch_report(report_url, "application/xml")
    print(report_response.text.strip())
except RuntimeError as error:
    print("Error:", error)
