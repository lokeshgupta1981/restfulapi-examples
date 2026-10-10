"""Opens the test host in headless Chromium, clicks in the view, prints the host log, saves a screenshot.

Needs: pip install playwright && playwright install chromium
Run (server on 127.0.0.1:8000): python3 browser_check.py
"""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 820, "height": 690}, device_scale_factor=1.25)
    page.goto("http://127.0.0.1:8000/host")
    view = page.frame_locator("iframe")
    view.locator("#rows tr").nth(2).wait_for()  # three items rendered from ui/notifications/tool-result
    view.locator("button[data-sku='MS-02']").click()
    view.locator("#status", has_text="MS-02 stock is").wait_for()
    view.locator("#export").click()
    view.locator("#status", has_text="Export refused").wait_for()
    page.wait_for_timeout(300)
    print("\n".join(page.evaluate("window.hostLog")))
    print("view status line:", view.locator("#status").inner_text())
    page.screenshot(path="screenshot.png")
    browser.close()
