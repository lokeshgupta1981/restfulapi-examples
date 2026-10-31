Source code for the article [OAuth Scopes Explained: Request, Grant and Enforce](https://restfulapi.net/oauth-scopes/)

A Bookstore API that checks OAuth scopes on every endpoint, a demo authorization server that decides which scopes to grant, and two clients. The examples show:

- how a client requests scopes and why the granted scope can be smaller than the requested one (RFC 6749, section 3.3)
- an unknown scope rejected with `invalid_scope`
- the `scope` claim inside a JWT access token (RFC 9068)
- 401 without a token or with a bad token, 403 with `error="insufficient_scope"` and the missing scope in `WWW-Authenticate` (RFC 6750)
- why a scope is not enough: Asha's token with `orders:read` still cannot read Meera's order
- how a role limits what a user can grant: only staff get `orders:refund`
- a client that starts with read-only scopes and asks for more after a 403 (step-up)
- the scopes listed in protected resource metadata (RFC 9728)

`auth_server.py` is a DEMO authorization server for learning only. It has no login page and no consent screen: the demo user named in `login_hint` is signed in automatically. Use Keycloak, Auth0, Okta, Microsoft Entra ID or another real authorization server in production. The client secret in the code is a fake demo value.

## Files

| File | Port | What it does |
|---|---|---|
| auth_server.py | 8000 | Authorization code flow with PKCE, JWT access tokens with `scope` and `roles`, JWKS, metadata |
| bookstore_api.py | 8001 | `GET /books`, `GET /orders`, `GET /orders/{id}`, `POST /orders`, `POST /orders/{id}/refund`, protected resource metadata |
| oauth_client.py | - | Shared client code for the authorization code flow |
| get_token.py | - | Prints a token response for a client, user and scope (`-v` prints the redirect) |
| client.py | - | The web shop client with step-up on `insufficient_scope` |
| demo.sh | - | Every case from the article with curl (needs curl and jq) |

## Demo clients and users

| Client | Secret | Scopes it may receive |
|---|---|---|
| bookshop-web | none (public client, PKCE) | books:read orders:read orders:write orders:refund |
| reading-tracker | demo-secret-reading-tracker | books:read orders:read |

| User | Role | Scopes the user may grant |
|---|---|---|
| asha | customer | books:read orders:read orders:write |
| ravi | staff | books:read orders:read orders:write orders:refund |

## Versions

- Python 3.13.18 (3.10 or newer works)
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1, python-multipart 0.0.32
- curl and jq (for demo.sh)

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/oauth-scopes-example
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn auth_server:app --port 8000      # terminal 1
uvicorn bookstore_api:app --port 8001    # terminal 2
./demo.sh                                # terminal 3
python client.py                         # terminal 3
```

To use other ports, set `ISSUER` and `API_URL` in every terminal, for example `export ISSUER=http://127.0.0.1:9000 API_URL=http://127.0.0.1:9001`, and start the servers on those ports. Restart the API to reset the orders.

OUTPUTS.txt holds the output of one run on Linux (2026-10-31).
