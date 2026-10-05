Source code for the article [x-www-form-urlencoded vs multipart/form-data vs JSON](https://restfulapi.net/form-urlencoded-vs-multipart-vs-json/)

A support-ticket API that accepts the same ticket as `application/x-www-form-urlencoded`, `multipart/form-data` and `application/json`, built three times (Express, FastAPI, Spring Boot). A raw socket server prints the exact bytes that curl, `fetch()`, Python requests and a browser form send for each format.

## Versions

- Python 3.13: fastapi 0.142.2, python-multipart 0.0.32, uvicorn 0.54.0, requests 2.34.2, urllib3 2.8.0, playwright 1.56.0 (see `requirements.txt`)
- Node.js 22: express 5.2.1, multer 2.4.0 (see `express/package.json`)
- JDK 21 and Maven 3.9: Spring Boot 4.1.1 (`spring-boot-starter-webmvc`)
- curl 8.5.0 (`--json` needs curl 7.82.0 or later)

## Folders and ports

| Folder / file | Port | What it does |
|---|---|---|
| `capture/wire_server.py` | 9170 | Prints every request byte for byte. `GET /form` serves three HTML forms (urlencoded, multipart, text/plain). |
| `express/server.mjs` | 9171 | `POST /tickets` accepts all three formats, returns HTTP 415 for others. `POST /tickets/with-attachment` reads a JSON part plus a file. `POST /oauth/token` is a form-encoded OAuth 2.0 token endpoint (demo client `ticket-cli` / `s3cret`). |
| `fastapi/app.py` | 9172 | `POST /tickets` (JSON), `POST /tickets/form` (form fields), `POST /tickets/upload` (multipart with a file). |
| `spring/` | 9173 | `POST /tickets` with three methods selected by `consumes`, plus `POST /tickets/with-attachment` (JSON part plus file part). |

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/form-urlencoded-vs-multipart-vs-json-example

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# start the four servers (one terminal each, or add & at the end)
python capture/wire_server.py
(cd express && npm install && npm start)
(cd fastapi && uvicorn app:app --port 9172)
(cd spring && mvn -q package -DskipTests && java -jar target/tickets-spring-1.0.0.jar)

# 1. what each client puts on the wire (watch the wire_server.py terminal)
bash capture/curl_clients.sh
node capture/fetch_clients.mjs
python capture/requests_clients.py
python capture/browser_forms.py

# 2. how Express, FastAPI and Spring Boot parse each format, and the common mistakes
bash curl_servers.sh
node mistakes_fetch.mjs
python mistakes_requests.py
node json_part_fetch.mjs

# 3. body size of the same data in each format
python sizes.py
```

Run every command from this folder (the clients read `error.log` from here). `OUTPUTS.txt` holds the output of one full run; multipart boundaries are random, so they differ on every run.
