# OAuth Protected Resource Metadata (RFC 9728) Example

Source code for the article [OAuth Protected Resource Metadata (RFC 9728)](https://restfulapi.net/oauth-protected-resource-metadata/)

An orders API publishes RFC 9728 protected resource metadata and points to it from its HTTP 401 and HTTP 403 responses. A Python client starts from the API URL alone, finds the authorization server, validates both metadata documents, gets a token for this API only, and calls the API. A curl script shows every HTTP exchange on the wire.

## Files

| File | Port | What it does |
|---|---|---|
| resource_server.py | 8000 | Orders API. Serves `/.well-known/oauth-protected-resource/orders` with `Cache-Control: max-age=3600`, answers 401 and 403 with `WWW-Authenticate: Bearer resource_metadata="...", scope="orders:read"`, and rejects tokens issued for another resource |
| auth_server.py | 9000 | Test authorization server with RFC 8414 metadata, a client credentials token endpoint and token introspection (RFC 7662). For local testing only |
| discover.py | - | The client. Follows the `resource_metadata` URL, or builds the path-based and root well-known URLs when the header has none, and stops when `resource` does not match the URL it called |
| demo.sh | - | Raw HTTP exchanges with curl: the 401, both metadata documents, a 404 for the wrong well-known URL, a token request, and the 403 and 401 for a wrong scope and a wrong resource |
| run_all.sh | - | Starts both servers, runs everything above plus the two failure modes, and writes OUTPUTS.txt |

The example uses `http` on 127.0.0.1. A real resource identifier uses `https`.

The client ID `orders-cli` and the secret `orders-cli-secret` are demo values. Never use them outside this example.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, python-multipart 0.0.32
- The client uses only the standard library; demo.sh needs curl

## How to Run

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_all.sh
```

Or step by step, each in its own terminal:

```bash
uvicorn auth_server:app --port 9000
uvicorn resource_server:app --port 8000
python discover.py http://127.0.0.1:8000/orders
./demo.sh
```

Two environment variables on the API change its behaviour:

- `PRM_NO_HEADER=1` leaves `resource_metadata` out of the 401 challenge. The client then builds the well-known URL itself and still succeeds.
- `PRM_FAKE_RESOURCE=1` publishes metadata for another resource with another authorization server. The client stops at step 3 with exit code 1.

## Expected Output

```text
1. GET http://127.0.0.1:8000/orders -> HTTP 401
   WWW-Authenticate: Bearer resource_metadata="http://127.0.0.1:8000/.well-known/oauth-protected-resource/orders", scope="orders:read"
2. GET http://127.0.0.1:8000/.well-known/oauth-protected-resource/orders -> HTTP 200
   {"resource": "http://127.0.0.1:8000/orders", "authorization_servers": ["http://127.0.0.1:9000"], ...}
3. resource matches the URL we called
4. GET http://127.0.0.1:9000/.well-known/oauth-authorization-server -> HTTP 200
   token_endpoint: http://127.0.0.1:9000/token
5. POST http://127.0.0.1:9000/token -> HTTP 200, scope 'orders:read', expires_in 600
6. GET http://127.0.0.1:8000/orders with token -> HTTP 200, 2 orders
```

OUTPUTS.txt holds the full output of one run of run_all.sh on Linux (2026-10-31). Dates and access tokens differ on every run.
