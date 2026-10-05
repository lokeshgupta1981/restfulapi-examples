Source code for the article [Long Polling vs SSE vs WebSockets](https://restfulapi.net/long-polling-vs-sse-vs-websockets/)

# Long polling, server-sent events and WebSocket on one server

One FastAPI app keeps an in-memory event log of order status changes and delivers it in three ways:

| Endpoint | Technique |
|---|---|
| `GET /orders/{id}/updates?after=N` | Long polling. Returns at once when events newer than `N` exist, otherwise holds the request for up to 25 s (`LONG_POLL_WAIT`) and returns an empty list. |
| `GET /orders/{id}/stream` | Server-sent events (`text/event-stream`). Sends `retry: 3000`, one `id`/`event`/`data` block per event, a `: ping` comment every 15 s (`HEARTBEAT`), and resumes from the `Last-Event-ID` request header (or `?after=N`). |
| `WS /orders/{id}/socket?after=N` | WebSocket. Sends each event as a JSON text message and accepts `{"action": "cancel"}` from the client. |
| `POST /orders/{id}/events` | Publishes an event, body `{"status": "shipped"}`. |
| `POST /admin/drop-connections` | Closes every open SSE stream and WebSocket (close code 1012), to test reconnection. |

Files:

- `server.py`: the app.
- `index.html`: browser page served at `/` with one panel per technique (`fetch()` loop, `EventSource`, `WebSocket` with reconnect and backoff).
- `demo.sh`: curl calls that show the wire format of each technique.
- `ws_client.py`: WebSocket client that receives an event and sends a message on the same connection.
- `measure.py`: runs one client per technique at the same time through small byte-counting TCP proxies (ports 9152-9154) and prints latency, requests and bytes. `NETWORK_DELAY_MS=50` adds a one-way delay, `WS_DEFLATE=1` turns on WebSocket compression.
- `nginx-proxy.conf`: nginx settings for all three techniques.
- `OUTPUTS.txt`: output captured from these scripts.

## Versions

- Python 3.13 (3.11 or later works)
- fastapi 0.142.2, uvicorn[standard] 0.54.0, websockets 17.2, httpx 0.28.1
- curl 8.x for `demo.sh`
- nginx 1.24.0 for `nginx-proxy.conf` (optional)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/long-polling-vs-sse-vs-websockets-example
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn server:app --port 9150     # terminal 1
./demo.sh                          # terminal 2 (takes about 35 s)
python measure.py 20 0.5           # 20 events, one every 500 ms
NETWORK_DELAY_MS=50 python measure.py 20 0.02
python measure.py 20 0.5 60        # also measures 60 s of idle time
```

Open http://127.0.0.1:9150/ in a browser, publish a few events, then run

```bash
curl -X POST http://127.0.0.1:9150/admin/drop-connections
```

and publish again: all three panels catch up without losing an event. The server log shows the SSE reconnect with `Last-Event-ID`.

The event log lives in memory, so restart the server to start from event id 1 again.
