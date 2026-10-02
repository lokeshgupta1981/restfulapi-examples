Source code for the article [Streaming LLM Responses in REST APIs with Server-Sent Events](https://restfulapi.net/streaming-llm-responses-server-sent-events/) on restfulapi.net.

A FastAPI REST endpoint, `POST /v1/answers/stream`, that calls an OpenAI-style LLM with streaming turned on and relays the answer to clients as server-sent events (`event: token`, `event: done` with token usage, `event: error`). It sends `: ping` heartbeats while the model is quiet and closes the upstream LLM request when the client disconnects. A fake LLM is included, so no API key is needed.

## Tested with

- Python 3.11.15 on Ubuntu 24.04
- fastapi 0.142.2, uvicorn 0.54.0, httpx 0.28.1, tiktoken 0.14.0 (see `requirements.txt`)
- curl 8.5.0, Chromium (via Playwright) for the browser page
- nginx 1.24.0 (optional, for the proxy buffering test)

## Files

- `fake_llm.py`: stand-in LLM provider (OpenAI-style streaming chunks, real token counts)
- `app.py`: the REST API that relays the stream as clean SSE events
- `client.py`: Python client with a small SSE parser and timings
- `static/index.html`: browser page that reads the stream with `fetch()` and a `ReadableStream` parser
- `nginx.conf`: optional nginx in front of the API, with and without buffering

## Run

```
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/streaming-llm-sse-example
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# terminal 1: the fake LLM
uvicorn fake_llm:app --port 9301

# terminal 2: the API (heartbeat every second, to see it in a short demo)
HEARTBEAT_SECONDS=1 uvicorn app:app --port 9300
```

Then try the clients:

```
curl -N -X POST http://127.0.0.1:9300/v1/answers/stream \
  -H "Content-Type: application/json" -d '{"question": "What are server-sent events?"}'

python client.py "What are server-sent events?"
python client.py "What are server-sent events?" --stop-after 10   # disconnect early
python client.py "What are server-sent events?" --model fake-broken      # upstream fails mid-stream
python client.py "What are server-sent events?" --model fake-error       # upstream sends an error object mid-stream
python client.py "What are server-sent events?" --model fake-overloaded  # upstream busy before streaming (HTTP 503 + Retry-After)
```

Open http://127.0.0.1:9300/ in a browser for the page with Ask and Stop buttons.

To use a real provider, set `UPSTREAM_URL` to its base URL without `/v1` (for example `https://api.openai.com`) and add your API key as an `Authorization` header on the `httpx.AsyncClient` in `app.py`.

## Optional: nginx buffering test

```
mkdir -p tmp
nginx -p "$PWD" -c nginx.conf
python client.py "Hi" --url http://127.0.0.1:9380/v1/answers/stream
python client.py "Hi" --url http://127.0.0.1:9380/buffered/v1/answers/stream
nginx -p "$PWD" -c nginx.conf -s stop
```

The second route ignores the `X-Accel-Buffering: no` header, so nginx 1.24 buffers the whole answer and the client gets it in one piece at the end.
