"""Opens the page in headless Chromium and runs three cross-origin fetch() calls."""
from playwright.sync_api import sync_playwright

CASES = [
    ("/orders", "text/plain"),
    ("/orders", "application/json"),
    ("/legacy-orders", "application/json"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda msg: print("browser console:", msg.text) if msg.type == "error" else None)
    page.goto("http://127.0.0.1:9310/")
    for path, content_type in CASES:
        print(page.evaluate("([p, c]) => send(p, c)", [path, content_type]), flush=True)
        page.wait_for_timeout(300)
    browser.close()
