"""Call each /cache URL three times from Chromium and count how many calls reached the server."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:9190"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(BASE + "/hits")
    for path in ("/cache/307", "/cache/308", "/cache/308?cc=no-store"):
        for _ in range(3):
            page.evaluate("url => fetch(url).then(r => r.text())", BASE + path)
    print("Chromium", browser.version)
    print("Server hits after 3 fetch() calls per URL:", page.evaluate("url => fetch(url).then(r => r.json())", BASE + "/hits"))
    browser.close()
