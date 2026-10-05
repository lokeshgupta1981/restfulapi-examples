Source code for the article [HTTP 302 Found](https://restfulapi.net/http-status-302-found/)

# An invoices API that answers with HTTP 302, and how clients follow it

The FastAPI app redirects `GET /invoices/{id}/pdf` to a temporary file-store URL with HTTP 302. A second endpoint, `/redirect/{code}`, redirects any method to `/echo` with HTTP 302, 303 or 307, so we can see which method and body each HTTP client sends after the redirect.

## Versions

- Python 3.13: FastAPI 0.142.2, uvicorn 0.54.0, requests 2.34.2, httpx 0.28.1, pytest 9.1.1 (pinned in requirements.txt)
- Node.js 22 with Express 5.2.1 (pinned in package.json)
- Java 21 (java.net.http.HttpClient)
- curl 8.5.0

## Files

| File | What it does |
|---|---|
| app.py | Invoices API on port 9182: the HTTP 302 PDF redirect, `/redirect/{code}` and `/echo` |
| express-app.js | The same PDF redirect in Express on port 9183, using the `res.redirect()` default |
| matrix.py | POST, PUT and DELETE through HTTP 302, 303 and 307 with requests and httpx, plus the Authorization header check |
| matrix.mjs | The same test with the Node.js `fetch()` |
| Matrix.java | The same test with Java HttpClient (`Redirect.NORMAL`) |
| no_follow.py, no_follow.mjs | Read the HTTP 302 instead of following it (requests `allow_redirects=False`, fetch `redirect: "manual"`) |
| test_app.py | pytest checks for the status code, `Location` and `Cache-Control` |
| run-demo.sh | Starts both servers, runs curl and every client, stops the servers |
| OUTPUTS.txt | Output of one run of run-demo.sh and pytest |

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm install
./run-demo.sh
.venv/bin/pytest -q
```

## Results

Method that reached `/echo` after the client followed the redirect:

| Sent | Status | curl -L | requests, httpx | fetch(), Java HttpClient |
|---|---|---|---|---|
| POST | 302 | GET | GET | GET |
| PUT | 302 | PUT without body | GET | PUT with body |
| DELETE | 302 | DELETE without body | GET | DELETE with body |
| POST | 303 | GET | GET | GET |
| PUT, DELETE | 303 | same method without body | GET | GET |
| any | 307 | same method with body | same method with body | same method with body |
