Source code for the article [HTTP 207 Multi-Status](https://restfulapi.net/http-status-207-multi-status/)

# A bulk cancel endpoint that answers with HTTP 207, and a WebDAV server for comparison

The Express app exposes `POST /orders/bulk-cancel`. It cancels each order in the `items` array on its own and returns HTTP 207 with one result per item (HTTP 200, 404 or 409), each error as a Problem Details object. A malformed body gets HTTP 400 and an empty or oversized `items` array gets HTTP 422, because those failures belong to the whole request.

A WsgiDAV server shows where HTTP 207 comes from: a WebDAV `PROPFIND` and a `DELETE` of a folder that holds a locked file both return an XML `multistatus` body.

## Versions

- Node.js 22.22.0 with Express 5.2.1 (pinned in package.json)
- Python 3.13 with WsgiDAV 4.3.5, Cheroot 11.1.2 and requests 2.34.2 (pinned in requirements.txt)
- Java 21 with Spring Boot 4.1.1 (pinned in spring-boot/pom.xml), built with Maven
- curl 8.5.0

## Files

| File | What it does |
|---|---|
| server.js | Orders API on port 9207 with the bulk cancel endpoint |
| client.mjs | Calls the endpoint with `fetch()` and lists the failed items |
| client.py | The same call with Python requests; shows that `raise_for_status()` does not raise for HTTP 207 |
| test.mjs | `node:test` check for the status code and the per-item results |
| spring-boot/ | The same bulk cancel endpoint in Spring Boot on port 9209, returning `HttpStatus.MULTI_STATUS` |
| run-demo.sh | Starts the Express app and WsgiDAV (port 9208), runs every curl call and client, stops both |
| OUTPUTS.txt | Output of one run of run-demo.sh and npm test |

## Run

```bash
npm install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
(cd spring-boot && mvn -q package -DskipTests)
./run-demo.sh
npm test
```

The orders live in memory, so restarting `server.js` resets them. The script `run-demo.sh` recreates the `webdav-data` folder on every run.
