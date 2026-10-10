Source code for the article [What Is an OpenAI-Compatible API](https://restfulapi.net/openai-compatible-api/)

# OpenAI-compatible API example

A small OpenAI-compatible server for the Chat Completions API, and a checker that tests any server with the official OpenAI Python SDK.

- `server.py` is a FastAPI server with `GET /v1/models`, `GET /v1/models/{model}` and `POST /v1/chat/completions`. It returns OpenAI error bodies (`{"error": {"message", "type", "param", "code"}}`) with matching status codes, limits each key to 10 requests per 10 seconds (HTTP 429 with `Retry-After` and `x-ratelimit-*` headers), and streams `chat.completion.chunk` events with `stream_options.include_usage` and `data: [DONE]`. The "model" repeats the last user message in upper case. With `LENIENT=1` it ignores `n` instead of rejecting it.
- `check_compat.py` runs nine checks with the SDK against any server set by `OPENAI_BASE_URL`, `OPENAI_API_KEY` and `MODEL`. The rate limit check runs only when `BURST_KEY` holds a second valid key, because it sends up to 21 requests.
- `switch_demo.py` creates clients for OpenAI, Ollama and the example server, and calls the example server.
- `wire.sh` prints the raw model list, an error response and a stream with curl.

## Versions

Python 3.13, FastAPI 0.143.0, Uvicorn 0.54.0, openai 3.28.0.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: run the scripts in Git Bash or WSL
pip install -r requirements.txt
./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run.

## Check another server

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1   # for example a local Ollama server
export OPENAI_API_KEY=any-value
export MODEL=llama3.2
python3 check_compat.py
```
