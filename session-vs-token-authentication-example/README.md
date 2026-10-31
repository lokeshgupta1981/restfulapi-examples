Source code for the article [Session vs Token Authentication (JWT vs Sessions)](https://restfulapi.net/session-vs-token-authentication/)

A small bookstore orders API (FastAPI) that supports two login styles side by side:

- **Session authentication**: `POST /session/login` stores a random session ID on the server and returns it in an
  `HttpOnly; Secure; SameSite=Lax` cookie. Every request looks the ID up in the session store.
- **Token authentication**: `POST /token/login` returns a signed JWT (HS256, 15 minutes). Every request checks the
  signature and the `exp` claim; no lookup, unless the denylist is switched on.

`demo.sh` starts two instances (A and B) and shows, with curl:

1. the `Set-Cookie` response of a session login,
2. a session cookie that works on A but not on B when sessions live in process memory,
3. a JWT that works on both instances, and its payload decoded without any key,
4. a tampered JWT rejected with 401,
5. the size of the `Cookie` and `Authorization` headers,
6. logout: the session is gone at once, the JWT keeps working,
7. a demoted user: the session sees the new role at once, the JWT keeps the old `role` claim,
8. after a restart with `SESSION_STORE=shared` and `DENYLIST=1`: sessions work across instances and a logged-out JWT is rejected.

## Files

| File | What it does |
|---|---|
| server.py | The API. Env vars: `INSTANCE`, `SESSION_STORE` (memory or shared), `DENYLIST` (0 or 1), `DATA_DIR` |
| demo.sh | Starts instances A and B on `BASE_PORT` and `BASE_PORT+1` (default 8000/8001), runs every scenario |
| OUTPUTS.txt | Output of one run |
| requirements.txt | Pinned Python packages |

The shared SQLite file (`data/shared.db`) stands in for a shared session store such as Redis.

## Versions

- Python 3.13
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1
- curl 8.5.0

## How to run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PY=.venv/bin/python ./demo.sh
```

Run a single instance by hand:

```
INSTANCE=A SESSION_STORE=memory .venv/bin/python -m uvicorn server:app --port 8000
```

The user `alice` / `alice-demo-pass` and the JWT secret in server.py are fake demo values. Never use them in production.
The `/demo/users/{name}/role/{role}` endpoint has no protection on purpose; it only exists to show the stale-claim problem.
