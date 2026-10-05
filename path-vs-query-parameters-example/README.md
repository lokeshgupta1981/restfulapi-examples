Source code for the article [Path vs Query Parameters in REST APIs](https://restfulapi.net/path-vs-query-parameters/)

A small Orders and Products API in FastAPI. It shows path parameters that identify a resource, query parameters that filter, sort, page and shape the response, defaults, HTTP 404 versus HTTP 422 for bad values, repeated query keys, percent-encoding cases, an nginx cache keyed on the query string, the nginx URL length limit and the HTTP QUERY method.

## Versions

- Python 3.13
- fastapi 0.142.2 (pulls in starlette 1.7.0 and pydantic 2.13.5)
- uvicorn 0.54.0 (h11 0.16.0)
- nginx 1.24.0 (only for the cache, length limit and access log demos)
- Node.js 22 (only for `encoding_demo.mjs` and `node_url_limit.mjs`)
- curl 8.5.0

## Files

- `app.py`: the API.
- `nginx/nginx.conf`: reverse proxy on port 8481 with a small cache. The directives `large_client_header_buffers` and `proxy_cache_key` keep their defaults.
- `run_demo.sh`: sends every request from the article.
- `encoding_demo.py`, `encoding_demo.mjs`: how Python and JavaScript encode query strings and path segments.
- `node_url_limit.mjs`: sends long URLs to a plain Node.js server to show its default header size limit (port 8482).
- `OUTPUTS.txt`: output of `run_demo.sh` from a real run.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1: the API on port 8480
uvicorn app:app --port 8480

# Terminal 2: nginx on port 8481 (Linux or macOS)
mkdir -p nginx/tmp nginx/cache
nginx -p "$PWD/nginx" -c nginx.conf

# Terminal 3: all requests from the article
./run_demo.sh

# Stop nginx when done
nginx -p "$PWD/nginx" -c nginx.conf -s stop
```

Without nginx, sections 5 to 7 of `run_demo.sh` and the second request of section 8 fail; everything else talks to uvicorn or runs on its own.

The interactive API docs are at http://localhost:8480/docs while uvicorn runs.
