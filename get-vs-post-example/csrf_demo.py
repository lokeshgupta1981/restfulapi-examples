"""Opens three cross-site pages in Chromium while the user is logged in to the Orders API.

The API runs on http://localhost:9120 and sets a SameSite=Lax session cookie.
The attacker pages run on http://127.0.0.1:9123, which is a different site.
"""
import json
import time
import urllib.request

from playwright.sync_api import sync_playwright

API = "http://localhost:9120"
ATTACKER = "http://127.0.0.1:9123"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"{API}/login")
    print("browser:", browser.version)
    print("cookie:", [(c["name"], c["sameSite"]) for c in page.context.cookies()])

    for attack in ["link-get.html", "img-get.html", "form-post.html"]:
        page.goto(f"{ATTACKER}/{attack}")
        page.wait_for_load_state("networkidle")
        time.sleep (0.5)
    browser.close()

with urllib.request.urlopen(f"{API}/cancel-log") as response:
    for entry in json.load(response):
        print(entry)
