# OAuth 2.0 Protected Resource Metadata (RFC 9728) example

Source code for the article https://restfulapi.net/oauth-protected-resource-metadata/

An orders API publishes RFC 9728 protected resource metadata and points to it from its HTTP 401 responses. A Python client starts from the API URL alone, finds the authorization server, validates both metadata documents, gets a token and calls the API.

- `resource_server.py`: orders API on port 8000. Serves `/.well-known/oauth-protected-resource/orders`, answers 401 and 403 with `WWW-Authenticate: Bearer resource_metadata="...", scope="orders:read"`, and rejects tokens issued for another resource.
- `auth_server.py`: test authorization server on port 9000 with RFC 8414 metadata, a client credentials token endpoint and token introspection. For local testing only.
- `discover.py`: the client. It follows the `resource_metadata` URL, or tries the path-based and root well-known URLs when the header has none, and stops when `resource` does not match the URL it called.

The example uses `http` on 127.0.0.1. A real resource identifier uses `https`.

## Versions

Python 3.10 or later, FastAPI 0.143.0, Uvicorn 0.54.0, python-multipart 0.0.32. The client uses only the standard library.

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# terminal 1
uvicorn auth_server:app --port 9000
# terminal 2
uvicorn resource_server:app --port 8000
# terminal 3
python discover.py http://127.0.0.1:8000/orders
```

## Expected output

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

## Test the validation rule

Restart the API with `PRM_FAKE_RESOURCE=1` (PowerShell: `$env:PRM_FAKE_RESOURCE=1`). The metadata then describes another resource, and the client stops at step 3 with exit code 1.

```text
3. STOP: resource 'https://orders.attacker.example/orders' does not match 'http://127.0.0.1:8000/orders', metadata not used
```

## Test scope and audience errors with curl

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:9000/token -d grant_type=client_credentials \
  -d client_id=orders-cli -d client_secret=orders-cli-secret \
  -d scope=orders:write -d resource=http://127.0.0.1:8000/orders | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/orders
# HTTP 403, WWW-Authenticate: Bearer error="insufficient_scope", resource_metadata="...", scope="orders:read"
```

A token requested with `resource=https://other.example/api` gets HTTP 401 with `error="invalid_token"`.
