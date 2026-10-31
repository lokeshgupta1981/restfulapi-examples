Source code for the article [OAuth 2.1 vs OAuth 2.0: What Changed and What to Update](https://restfulapi.net/oauth-2-1-vs-oauth-2-0/)

One demo authorization server with a small Bookstore API, started twice: once with the original OAuth 2.0 rules (RFC 6749, RFC 6750) and once with the OAuth 2.1 rules (draft-ietf-oauth-v2-1-16). A client sends the same requests to both and prints the answers: the implicit grant, the password grant, the authorization code without PKCE, the PKCE `plain` method, a look-alike redirect URI, the `iss` parameter, a bearer token in the query string, and a refresh token used twice.

`server.py` is a DEMO authorization server for learning only. It has no login page and signs in the demo user `asha` automatically. Use Keycloak, Auth0, Okta, Microsoft Entra ID or another real authorization server in production. The password in the code is a fake demo value.

## Files

- `server.py`: demo authorization server (`/authorize`, `/token`) plus `GET /books`. `OAUTH_PROFILE` selects `2.0` or `2.1` (default); `ISSUER` sets the issuer identifier returned as `iss` under 2.1.
- `client.py`: sends the eight test requests to each server URL given on the command line and prints one line per test.
- `demo.sh`: the same exchanges with curl, showing the raw `Location` headers and JSON responses, plus refresh token rotation.
- `raw.sh`: full HTTP responses (`curl -i`) for the code + PKCE flow, the password grant, a token in the query string and a refresh token used twice.
- `OUTPUTS.txt`: output of one run of all three scripts.

## Versions

- Python 3.13.18 (3.10 or newer works)
- fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1, python-multipart 0.0.32
- curl 8.5.0, OpenSSL 3.0.13, GNU coreutils 9.4 (`basenc`), jq 1.7 (`demo.sh` only)

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/oauth-2-1-vs-oauth-2-0-example
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1: OAuth 2.0 rules
OAUTH_PROFILE=2.0 ISSUER=http://127.0.0.1:8000 uvicorn server:app --port 8000

# Terminal 2: OAuth 2.1 rules
OAUTH_PROFILE=2.1 ISSUER=http://127.0.0.1:8001 uvicorn server:app --port 8001

# Terminal 3
python client.py http://127.0.0.1:8000 http://127.0.0.1:8001
./demo.sh
./raw.sh
```

On Windows, set the variables with `set OAUTH_PROFILE=2.0` before starting uvicorn. `demo.sh` and `raw.sh` use `http://127.0.0.1:8000` and `http://127.0.0.1:8001`; for other ports, set `V20` and `V21`, for example `V20=http://127.0.0.1:9000 V21=http://127.0.0.1:9001 ./demo.sh`.

Restart the servers to clear the in-memory codes and tokens.
