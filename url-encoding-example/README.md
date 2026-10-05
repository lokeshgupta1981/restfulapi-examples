Source code for the article [URL Encoding in REST APIs](https://restfulapi.net/url-encoding/)

A small document API (Python standard library) that shows how a server decodes the path and the query string, plus client scripts that encode the same values in Python, JavaScript, Java and curl.

## Versions

- Python 3.13 (server.py uses only the standard library), requests 2.34.2 for encode.py
- Node.js 22 (encode.mjs, no dependencies)
- JDK 21 (Encode.java and UrlBuilding.java, no dependencies; each runs as a single-file program)
- curl 8.5.0 (`--url-query` needs curl 7.87.0 or later)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/url-encoding-example

# terminal 1: the server listens on 127.0.0.1:9160 (change with PORT=...)
python3 server.py

# terminal 2
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python encode.py
node encode.mjs
java -Dstdout.encoding=UTF-8 Encode.java
java -Dstdout.encoding=UTF-8 UrlBuilding.java
bash demo.sh
```

## Endpoints

- `GET /v2/docs/{name}?tag=...` splits the path on `/`, decodes each segment once (UTF-8) and parses the query string with form rules (`+` is a space). A malformed escape or invalid UTF-8 in the path or the query gives HTTP 400.
- `GET /v1/docs/{name}` has a deliberate bug: the router decodes the path a second time.
- `GET /v1/admin/stats` and `GET /v2/admin/stats` are blocked by an access check (HTTP 403). The check runs on the path decoded once, so `/v1/%2561dmin/stats` gets past it.
- `POST /v2/notes` reads an `application/x-www-form-urlencoded` body and returns the decoded fields.
