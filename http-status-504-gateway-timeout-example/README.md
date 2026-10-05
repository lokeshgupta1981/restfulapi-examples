Source code for the article [HTTP 504 Gateway Timeout](https://restfulapi.net/http-status-504-gateway-timeout/)

# nginx timeouts in front of a slow FastAPI orders API

The project puts nginx in front of a FastAPI app with slow endpoints and short demo timeouts (proxy_connect_timeout 2s, proxy_read_timeout 3s), so that each kind of HTTP 504 shows up within a few seconds.

## Versions

- Python 3.13
- FastAPI 0.142.2, uvicorn 0.54.0 (pinned in requirements.txt)
- nginx 1.24.0 (the Ubuntu 24.04 package); any recent nginx works

## Files

| File | What it does |
|---|---|
| app.py | Orders API on port 9504 with slow endpoints, one endpoint that enforces its own 2-second budget, and an export job that answers HTTP 202 |
| stuck_listener.py | Port 9505 accepts no new TCP connections, so nginx hits proxy_connect_timeout |
| nginx.conf | Port 8504 proxies to both, and returns HTTP 504 as Problem Details JSON |
| run-demo.sh | Starts everything, runs every case with curl, prints the error.log, access log and app log |
| OUTPUTS.txt | Output of one run of run-demo.sh |

## Run

```bash
sudo apt-get install -y nginx        # or use your package manager
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run-demo.sh
```

nginx runs as your user with its prefix set to this folder, so the logs go to `logs/` and nothing in `/etc/nginx` changes. The whole run takes about 50 seconds.

## Cases

| Case | Request | What happens | Client sees |
|---|---|---|---|
| 0 | GET /reports/sales?seconds=1 | app answers in 1 s | HTTP 200 |
| 1 | GET /reports/sales?seconds=5 | app needs 5 s, nginx waits 3 s | HTTP 504 after 3 s; the app still finishes at 5 s |
| 2 | POST /orders?seconds=5 | app saves the order, then waits 5 s | HTTP 504, but GET /orders shows the order was created |
| 3 | GET /legacy/status | upstream never accepts the TCP connection | HTTP 504 after 2 s ("while connecting to upstream") |
| 4 | GET /reports/export | app streams one line every 2 s for 8 s | HTTP 200, because proxy_read_timeout is measured between two reads |
| 5 | GET /inventory | app gives up after its own 2 s budget | HTTP 503 with Retry-After, before nginx would time out |
| 6 | GET /reports/yearly | app needs 5 s, its nginx location sets proxy_read_timeout 10s | HTTP 200 after 5 s |
| 7 | POST /exports, then GET the Location URL | app starts a background job and answers at once | HTTP 202 with Location; status RUNNING, then DONE after 6 s |
