Source code for the article [WWW-Authenticate Header: Challenges and Examples](https://restfulapi.net/www-authenticate-header/)

# A Shipments API that sends WWW-Authenticate challenges, and clients that read them

The FastAPI app protects `/shipments` with Bearer tokens and answers every failure with a `WWW-Authenticate` challenge: no error code when no token was sent, `invalid_token`, `insufficient_scope` with `scope`, and `invalid_request`. Each challenge carries a `resource_metadata` URL (RFC 9728). `/v2/shipments` offers two challenges (Bearer and DPoP), `/legacy/reports` sends a Basic challenge, and a tiny forward proxy answers HTTP 407 with `Proxy-Authenticate`.

All tokens and passwords in this folder are fake demo values (`demo-token-read`, `demo-token-expired`, `demo-pass-123`, `demo-proxy-pass`).

## Versions

- Python 3.13: FastAPI 0.142.2, uvicorn 0.54.0, requests 2.34.2, Playwright 1.56.0 with Chromium 141 (pinned in requirements.txt)
- Node.js 22 (no npm dependencies; built-in `fetch()` and `node:test`)
- curl 8.5.0

## Files

| File | What it does |
|---|---|
| app.py | Shipments API on port 9420 (and a copy on port 9423 with `EXPOSE=0`, which does not expose `WWW-Authenticate` to browser scripts) |
| parse-challenges.mjs | Parser for `WWW-Authenticate` and `Proxy-Authenticate` values (RFC 9110 section 11.3) |
| parse-demo.mjs | Parses the RFC 9110 example value and prints the challenges as JSON |
| parse-challenges.test.mjs | Tests for the parser, including the RFC 9110 example |
| client.mjs | Node.js client that reads the challenge, loads the resource metadata and picks the next step |
| basic_client.py | Python requests: repeated header lines, `HTTPBasicAuth` and credentials in the URL |
| url_credentials.mjs | Shows that `fetch()` rejects a URL with a user name and password |
| proxy.py | Forward proxy on port 9424 that answers HTTP 407 without `Proxy-Authorization` |
| browser_check.py | Headless Chromium: which 401 responses open the login dialog, and whether page JavaScript can read the header cross-origin |
| web/index.html | Static page served on port 9421 (the second origin) |
| run-demo.sh | Starts all servers, runs curl and every client, stops the servers |
| OUTPUTS.txt | Output of one run of run-demo.sh |

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
./run-demo.sh
node --test
```

Ports used: 9420, 9421, 9423, 9424.
