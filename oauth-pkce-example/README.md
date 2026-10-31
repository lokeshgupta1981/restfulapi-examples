Source code for the article [OAuth PKCE Explained: How PKCE Protects the Code Flow](https://restfulapi.net/oauth-pkce/)

The authorization code flow with PKCE (RFC 7636), end to end: a public client (the "Bookstore" mobile app) creates a code verifier and an S256 code challenge, signs in, redeems the code with the verifier and calls an Orders API. A second script plays a malicious app that intercepts the authorization code, and shows that the stolen code works against a server without PKCE and fails with `invalid_grant` when PKCE is enforced.

`server.py` is a DEMO authorization server for learning only. It has no login page and signs in the demo user `asha` automatically. Use Keycloak, Auth0, Okta, Microsoft Entra ID or another real authorization server in production. There are no secrets in this folder: the client is a public client.

## Files

- `pkce.py`: creates a code verifier and its S256 code challenge, and checks the RFC 7636 Appendix B test vector.
- `pkce.mjs`: the same with the Web Crypto API, for the browser or Node.js 20+.
- `server.py`: demo authorization server (`/.well-known/oauth-authorization-server`, `/authorize`, `/token`) plus `GET /orders`. `PKCE_MODE` selects `required` (default), `optional` or `off`.
- `client.py`: the Bookstore app: checks the server metadata for S256, sends the authorization request, checks `state`, redeems the code with the verifier, calls `/orders`.
- `attack.py`: the malicious app: redeems an intercepted code without the verifier and with its own verifier. `--app-without-pkce` makes the real app skip PKCE.
- `demo.sh`: the same flow with curl, openssl and basenc, plus a second redemption of the same code and a request for the `plain` method.
- `OUTPUTS.txt`: output of one run of everything, for all three server modes.

## Versions

- Python 3.13.18 (3.10 or newer works)
- fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1, python-multipart 0.0.32
- Node.js 22.23.4 (`pkce.mjs` only)
- curl 8.5.0, OpenSSL 3.0.13, GNU coreutils 9.4 (`basenc`), jq 1.7 (`demo.sh` only)

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/oauth-pkce-example
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python pkce.py
node pkce.mjs

# Terminal 1: the demo server with PKCE enforced
uvicorn server:app --port 8000

# Terminal 2
python client.py
python attack.py
python attack.py --app-without-pkce
./demo.sh
```

To see the attack succeed, restart the server without PKCE and run `python attack.py` again:

```bash
PKCE_MODE=off uvicorn server:app --port 8000        # Windows: set PKCE_MODE=off
PKCE_MODE=optional uvicorn server:app --port 8000   # PKCE only when the client sends it
```

The scripts use `http://127.0.0.1:8000`. If you start the server on another port, set `AUTH_URL`, for example `AUTH_URL=http://127.0.0.1:9000 python client.py`.
