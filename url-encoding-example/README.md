Source code for the article [URL Encoding in REST APIs](https://restfulapi.net/url-encoding/)

A small document API that shows how a server decodes the path and the query string, plus client scripts that encode the same values in Python, JavaScript, Java and curl. A second, FastAPI version of the document route shows what a framework decodes for us.

## Files

- `server.py`: the document API on port 9160 (Python standard library only), so every decoding step is visible.
- `fastapi_app.py`: the same document route in FastAPI on port 9161.
- `encode.py`, `encode.mjs`, `Encode.java`: the encoders of each language, applied to the same four values, and requests to `server.py`.
- `demo.sh`, `demo_fastapi.sh`: curl requests against both servers.
- `OUTPUTS.txt`: the output of every script, captured from a real run.

## Versions

- Python 3.13, requests 2.34.2, FastAPI 0.162.0, uvicorn 0.54.0
- Node.js 22 (encode.mjs, no dependencies)
- JDK 25 (Encode.java, no dependencies; it runs as a single-file program)
- curl 8.5.0 (`--url-query` needs curl 7.87.0 or later)

## How to Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/url-encoding-example
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# terminal 1: the standard-library server on 127.0.0.1:9160 (change with PORT=...)
python server.py

# terminal 2: the FastAPI version on 127.0.0.1:9161
uvicorn fastapi_app:app --port 9161

# terminal 3 (activate the venv here too)
python encode.py
node encode.mjs
java -Dstdout.encoding=UTF-8 Encode.java
bash demo.sh
bash demo_fastapi.sh
```

## Endpoints of server.py

- `GET /v2/docs/{name}?tag=...` splits the path on `/`, decodes each segment once (UTF-8) and parses the query string with form rules (`+` is a space). A malformed escape or invalid UTF-8 in the path or the query gives HTTP 400.
- `GET /v1/docs/{name}` has a deliberate bug: the router decodes the path a second time.
- `GET /v1/admin/stats` and `GET /v2/admin/stats` are blocked by an access check (HTTP 403). The check runs on the path decoded once, so `/v1/%2561dmin/stats` gets past it.
- `POST /v2/notes` reads an `application/x-www-form-urlencoded` body and returns the decoded fields.

The JSON responses write non-ASCII characters as `\uXXXX` escapes, so `café` in the output is the word "cafe" with an accented e.
