"""Runs every CSRF scenario in a real Chromium browser (Playwright).

Alice logs in to the API in the browser, then visits an attacker page.
We print what the browser sent and whether her email address changed.

Needs api.py and two copies of attacker.py running:
  uvicorn api:app --port 8000
  uvicorn attacker:app --port 9000      (cross-site attacker, opened as 127.0.0.1)
  uvicorn attacker:app --port 9001      (same-site attacker, opened as localhost)
Override the URLs with API, CROSS_SITE and SAME_SITE environment variables.
Set WAIT_LAX=1 to add scenario 3b, which waits 125 seconds after login.
"""

import os
from urllib.parse import quote

from playwright.sync_api import sync_playwright

API = os.environ.get("API", "http://localhost:8000")
CROSS_SITE = os.environ.get("CROSS_SITE", "http://127.0.0.1:9000")  # another site
SAME_SITE = os.environ.get("SAME_SITE", "http://localhost:9001")    # same site, other origin

LOGIN_JS = """s => fetch('/login?samesite=' + s, {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'alice'})}).then(r => r.status)"""


def login(browser, samesite):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(API + "/")
    page.evaluate(LOGIN_JS, samesite)
    ctx.request.post(API + "/reset")
    cookie = ctx.cookies()[0]
    print(f"  cookie: session; SameSite={cookie['sameSite']}; Secure={cookie['secure']}")
    return ctx, page


def email_now(ctx):
    return ctx.request.get(API + "/api/me").json()["email"]


def form_attack(browser, title, samesite, attacker, endpoint, wait_seconds=0):
    print(f"\n== {title}")
    ctx, page = login(browser, samesite)
    if wait_seconds:
        print(f"  waiting {wait_seconds} s after login ...")
        page.wait_for_timeout(wait_seconds * 1000)
    target = API + endpoint
    url = f"{attacker}/form?target={quote(target)}"
    print(f"  alice opens {url.split('?')[0]} (form posts to {endpoint})")
    with page.expect_response(lambda r: r.url == target) as info:
        page.goto(url)
    resp = info.value
    req_headers = resp.request.all_headers()
    print(f"  browser sent cookie: {'yes' if 'session=' in req_headers.get('cookie', '') else 'no'}, "
          f"Sec-Fetch-Site: {req_headers.get('sec-fetch-site')}, "
          f"Content-Type: {req_headers.get('content-type')}")
    print(f"  body: {resp.request.post_data.strip()}")
    print(f"  API answered: {resp.status} {resp.text()[:90]}")
    print(f"  alice's email is now: {email_now(ctx)}")
    ctx.close()


def script_attack(browser, title, samesite, page_path):
    print(f"\n== {title}")
    ctx, page = login(browser, samesite)
    page.goto(f"{CROSS_SITE}{page_path}")
    page.wait_for_function("document.getElementById('out').textContent !== 'running'")
    print(f"  attacker page saw: {page.inner_text('#out')[:90]}")
    print(f"  alice's email is now: {email_now(ctx)}")
    ctx.close()


def own_page(browser):
    print("\n== Our own page (same origin) sends the CSRF token")
    ctx, page = login(browser, "lax")
    with page.expect_response(lambda r: r.url.endswith("/protected/email")) as info:
        page.click("#save")
    resp = info.value
    h = resp.request.all_headers()
    print(f"  browser sent cookie: {'yes' if 'session=' in h.get('cookie', '') else 'no'}, "
          f"Sec-Fetch-Site: {h.get('sec-fetch-site')}, X-CSRF-Token: {h.get('x-csrf-token', '-')[:16]}...")
    print(f"  API answered: {resp.status} {resp.text()}")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    print(f"Chromium {browser.version}")
    form_attack(browser, "1. SameSite=None, cross-site form -> /unsafe/email", "none", CROSS_SITE, "/unsafe/email")
    form_attack(browser, "2. SameSite=Lax, cross-site form -> /unsafe/email", "lax", CROSS_SITE, "/unsafe/email")
    form_attack(browser, "3. No SameSite attribute, cross-site form -> /unsafe/email", "unset", CROSS_SITE, "/unsafe/email")
    if os.environ.get("WAIT_LAX"):  # optional, takes over two minutes
        form_attack(browser, "3b. No SameSite attribute, cookie older than 2 minutes -> /unsafe/email",
                    "unset", CROSS_SITE, "/unsafe/email", wait_seconds=125)
    form_attack(browser, "4. SameSite=Lax, SAME-site form (other port) -> /unsafe/email", "lax", SAME_SITE, "/unsafe/email")
    form_attack(browser, "5. SameSite=Strict, SAME-site form (other port) -> /unsafe/email", "strict", SAME_SITE, "/unsafe/email")
    form_attack(browser, "6. SameSite=None, cross-site form -> /json-only/email", "none", CROSS_SITE, "/json-only/email")
    script_attack(browser, "7. SameSite=None, cross-site fetch() with application/json -> /unsafe/email",
                  "none", f"/fetch-json?target={quote(API + '/unsafe/email')}")
    form_attack(browser, "8. SameSite=None, cross-site form -> /protected/email", "none", CROSS_SITE, "/protected/email")
    form_attack(browser, "9. SameSite=Lax, SAME-site form -> /protected/email", "lax", SAME_SITE, "/protected/email")
    script_attack(browser, "10. Attacker page tries to read the CSRF token", "none", f"/read-token?api={quote(API)}")
    form_attack(browser, "11. Cross-site form -> /bearer/email (token lives in JavaScript, not in a cookie)",
                "none", CROSS_SITE, "/bearer/email")
    own_page(browser)
    browser.close()
