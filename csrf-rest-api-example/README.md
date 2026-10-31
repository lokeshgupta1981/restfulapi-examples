Source code for the article [CSRF Token in REST APIs: When Do You Need One?](https://restfulapi.net/csrf-rest-api/)

# CSRF in REST APIs example

A small bookstore account API (FastAPI) where alice can change her email address, an attacker site that tries to change it for her, and a script that runs every attack in a real Chromium browser.

The API has four versions of the same "change my email" endpoint:

- `POST /unsafe/email`: cookie session, reads the body as JSON whatever the `Content-Type` says. Vulnerable to CSRF.
- `POST /json-only/email`: cookie session, accepts `application/json` only (FastAPI rejects other bodies with HTTP 422).
- `POST /protected/email`: cookie session, rejects cross-origin requests with `Sec-Fetch-Site` (and `Origin` as a fallback), and requires a CSRF token in the `X-CSRF-Token` header. The token is an HMAC bound to the session.
- `POST /bearer/email`: reads a bearer token from the `Authorization` header and ignores cookies.

`POST /login?samesite=strict|lax|none|unset` sets the session cookie with the chosen `SameSite` attribute, so the demo can compare them. It also returns a bearer token.

## Files

- `api.py`: the API, plus `GET /api/csrf-token` and `GET /` (our own front end).
- `app.html`: the same-origin page that fetches a CSRF token and sends it with `fetch()`.
- `attacker.py`: the attacker site: an auto-submitting `text/plain` form, a cross-site `fetch()` with `application/json`, and a script that tries to read the CSRF token.
- `browser_demo.py`: logs alice in inside Chromium (Playwright), opens the attacker pages and prints what the browser sent and what the API answered.
- `demo.sh`: the same API called with curl: missing, valid and forged CSRF tokens, `Sec-Fetch-Site` and `Origin` checks, the `text/plain` body, and the bearer endpoint.
- `OUTPUTS.txt`: output of a real run, including the API request log.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, playwright 1.63.0 (pinned in `requirements.txt`)
- Chromium 153 installed by Playwright
- curl and bash for `demo.sh` (on Windows, use Git Bash or WSL)

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/csrf-rest-api-example
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium

uvicorn api:app --port 8000            # terminal 1: the API
uvicorn attacker:app --port 9000       # terminal 2: cross-site attacker (opened as 127.0.0.1)
uvicorn attacker:app --port 9001       # terminal 3: same-site attacker (opened as localhost)

python browser_demo.py                 # terminal 4
./demo.sh                              # terminal 4
```

`localhost` and `127.0.0.1` are different sites for the browser, so the attacker on `127.0.0.1:9000` is cross-site. `localhost:9001` is the same site as the API on `localhost:8000` (ports do not count for "site"), but a different origin.

Set `WAIT_LAX=1` before `python browser_demo.py` to add a scenario that waits 125 seconds after login. It shows that Chrome sends a cookie without a `SameSite` attribute on a cross-site POST only during the first two minutes.

Other ports: set `API`, `CROSS_SITE` and `SAME_SITE` for `browser_demo.py`, and `BASE` for `demo.sh`, for example `BASE=http://localhost:9500 ./demo.sh`.

The API uses a fake demo secret (`CSRF_SECRET`), in-memory sessions and no passwords. Do not use it as a login system.
