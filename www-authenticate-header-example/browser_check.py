"""Checks in headless Chromium:
1. Which 401 responses make the browser ask for a user name and password.
2. Whether page JavaScript can read WWW-Authenticate on a cross-origin response.

The DevTools Fetch domain reports an authRequired event whenever Chromium would show
its login dialog. The script cancels the dialog and records the event.
"""
from playwright.sync_api import sync_playwright

API = "http://127.0.0.1:9420"          # exposes WWW-Authenticate
API_NO_EXPOSE = "http://127.0.0.1:9423"  # same app, no Access-Control-Expose-Headers
PAGE_ORIGIN = "http://127.0.0.1:9421"  # a different origin that serves a static page

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    cdp = page.context.new_cdp_session(page)
    prompts = []

    def on_paused(event):
        cdp.send("Fetch.continueRequest", {"requestId": event["requestId"]})

    def on_auth(event):
        challenge = event["authChallenge"]
        prompts.append(challenge["scheme"] + " realm=" + challenge["realm"])
        cdp.send("Fetch.continueWithAuth", {
            "requestId": event["requestId"],
            "authChallengeResponse": {"response": "CancelAuth"},
        })

    cdp.on("Fetch.requestPaused", on_paused)
    cdp.on("Fetch.authRequired", on_auth)
    cdp.send("Fetch.enable", {"handleAuthRequests": True, "patterns": [{"urlPattern": "*"}]})

    def check(label, action):
        prompts.clear()
        status = action()
        page.wait_for_timeout(300)
        shown = "login dialog: " + prompts[0] if prompts else "no login dialog"
        print(label.ljust(52), "status", status, "|", shown)

    print("== Login dialog")
    check("navigate to /legacy/reports (Basic)",
          lambda: page.goto(API + "/legacy/reports").status)
    check("navigate to /shipments (Bearer)",
          lambda: page.goto(API + "/shipments").status)
    page.goto(API + "/")
    check("same-origin fetch /legacy/reports (Basic)",
          lambda: page.evaluate("fetch('/legacy/reports').then(r => r.status)"))
    check("same-origin fetch /shipments (Bearer)",
          lambda: page.evaluate("fetch('/shipments').then(r => r.status)"))
    page.goto(PAGE_ORIGIN + "/")
    check("cross-origin fetch /legacy/reports (Basic)",
          lambda: page.evaluate("fetch('" + API + "/legacy/reports').then(r => r.status)"))

    print("== Reading the header from a cross-origin page")
    script = """async (url) => {
        const response = await fetch(url, { headers: { Authorization: 'Bearer demo-token-expired' } });
        return response.status + ' ' + response.headers.get('WWW-Authenticate');
    }"""
    print("with Access-Control-Expose-Headers:   ", page.evaluate(script, API + "/shipments"))
    print("without Access-Control-Expose-Headers:", page.evaluate(script, API_NO_EXPOSE + "/shipments"))
    browser.close()
