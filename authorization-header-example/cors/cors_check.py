"""Opens the demo page in headless Chromium and sends five cross-origin fetch() calls."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda msg: print("browser console:", msg.text) if msg.type == "error" else None)
    page.goto("http://127.0.0.1:9780/")
    for path in ["/orders", "/orders-wildcard", "/redirect-same", "/redirect-port", "/redirect"]:
        print(page.evaluate("(p) => send(p)", path), flush=True)
        page.wait_for_timeout(300)
    browser.close()
