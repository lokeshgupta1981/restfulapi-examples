"""Submits the three HTML forms from GET /form in headless Chromium.
Start wire_server.py first. Run from the example root folder."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:9170"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for form_id in ["urlencoded", "multipart", "plain"]:
        page.goto(f"{BASE}/form")
        if form_id == "multipart":
            page.set_input_files("#multipart input[type=file]", "error.log")
        page.click(f"#{form_id} button")
        page.wait_for_load_state()
    browser.close()

print("submitted 3 forms")
