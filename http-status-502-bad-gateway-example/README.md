Source code for the article [HTTP 502 Bad Gateway](https://restfulapi.net/http-status-502-bad-gateway/)

# nginx in front of a FastAPI orders API that fails on purpose

The project puts nginx in front of a small FastAPI app and breaks the app in five ways, so that we can see which failures turn into HTTP 502 and what nginx writes to its error log for each one.

## Versions

- Python 3.13
- FastAPI 0.142.2, uvicorn 0.54.0, httpx 0.28.1 (pinned in requirements.txt)
- nginx 1.24.0 (the Ubuntu 24.04 package); any recent nginx works

## Files

| File | What it does |
|---|---|
| app.py | Orders API on port 9502 with four failure endpoints under /fail/ |
| nginx.conf | Port 8502 proxies with nginx defaults, except a 32k header buffer for /fail/huge-header; port 8503 proxies and returns HTTP 502 as Problem Details JSON |
| client.py | Retries HTTP 502, 503 and 504 for idempotent methods only, with backoff and Retry-After |
| run-demo.sh | Starts nginx and the app, runs every case with curl, prints the error.log lines |
| OUTPUTS.txt | Output of one run of run-demo.sh |

## Run

```bash
sudo apt-get install -y nginx        # or use your package manager
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run-demo.sh
```

nginx runs as your user with its prefix set to this folder (`nginx -p "$PWD" -c "$PWD/nginx.conf"`), so the logs go to `logs/` and nothing in `/etc/nginx` changes.

## Cases

| Case | Request | What the app does | Client sees | nginx error.log |
|---|---|---|---|---|
| 1 | GET /orders/1001 | app is not running | HTTP 502 | connect() failed (111: Connection refused) while connecting to upstream |
| 2 | GET /fail/crash-before-response | process exits before writing the response | HTTP 502 | upstream prematurely closed connection while reading response header from upstream |
| 3 | GET /fail/crash-mid-body | process exits halfway through the body | HTTP 200 with a cut-off body (curl exit code 18) | upstream prematurely closed connection while reading upstream |
| 4 | GET /fail/huge-header (port 8503) | sends a 16 KB response header | HTTP 502 (HTTP 200 on port 8502 with proxy_buffer_size 32k) | upstream sent too big header while reading response header from upstream |
| 5 | POST /fail/reset with a 900 KB body | process exits without reading the body, the kernel sends a TCP RST | HTTP 502 | recv() failed (104: Connection reset by peer) while reading response header from upstream |

To try a single case by hand, start the app and nginx yourself:

```bash
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 9502 &
mkdir -p logs tmp && nginx -p "$PWD" -c "$PWD/nginx.conf"
curl -i http://127.0.0.1:8503/fail/huge-header
tail -n 1 logs/error.log
nginx -p "$PWD" -c "$PWD/nginx.conf" -s stop
```
