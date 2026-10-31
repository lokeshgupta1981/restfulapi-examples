Source code for the article [Backend for Frontend (BFF) Pattern](https://restfulapi.net/backend-for-frontend-pattern/)

# A bookstore with a mobile BFF and a web BFF

The project runs three general-purpose services (orders, catalog, shipping), a tiny OAuth authorization server, and two Backends for Frontends:

- the **mobile BFF** turns four service calls into one request shaped for the mobile order screen, runs independent calls in parallel, and degrades the screen when the shipping service is down;
- the **web BFF** does the same for the desktop order page and is also the browser's OAuth client, as described in RFC 10017, Section 6.1: tokens stay on the server, the browser only gets an HttpOnly session cookie, and every API call needs an *X-CSRF: 1* header.

## Versions

- Python 3.13
- FastAPI 0.143.0, uvicorn 0.54.0, httpx 0.28.1, PyJWT 2.15.1 (pinned in requirements.txt)
- curl

## Files

| File | What it does |
|---|---|
| settings.py | Ports (default 8000-8005), URLs, FAKE demo keys, simulated service delay (SIM_DELAY_MS, default 80) |
| services.py | Three FastAPI apps: orders_app, catalog_app, shipping_app; orders and shipping require a bearer token |
| auth_server.py | Demo authorization server: /authorize (auto-signs in user "alice", PKCE S256) and /token (authorization_code and refresh_token grants) |
| mobile_bff.py | GET /mobile/v1/order-screen/{id}; FANOUT=sequential switches off the parallel calls for the benchmark |
| web_bff.py | /bff/login, /bff/callback, /bff/user, /bff/logout and GET /api/order-page/{id} with session cookie, CSRF header check and token refresh |
| mobile_client.py | Signs in as the mobile app and loads the order screen with and without the BFF |
| bench.py | Median time of the order screen: direct calls vs one BFF call |
| demo.sh | Starts everything, runs all steps of the article, stops only the processes it started |
| OUTPUTS.txt | Output of one run of demo.sh (BASE_PORT=20480) |

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./demo.sh                     # ports 8000-8005
BASE_PORT=20480 ./demo.sh     # or any other block of six free ports
```

To try it by hand, start the processes yourself (each in its own terminal):

```bash
.venv/bin/uvicorn auth_server:app --port 8000
.venv/bin/uvicorn services:orders_app --port 8001
.venv/bin/uvicorn services:catalog_app --port 8002
.venv/bin/uvicorn services:shipping_app --port 8003
.venv/bin/uvicorn mobile_bff:app --port 8004
.venv/bin/uvicorn web_bff:app --port 8005
.venv/bin/python mobile_client.py
```

The cookies use the `__Host-Http-` prefix and the `Secure` flag, so a real browser only stores them over HTTPS. The demo sends them with curl over plain HTTP on localhost. Everything here is for learning: the authorization server has no login page, sessions live in memory, and all keys are fake.
