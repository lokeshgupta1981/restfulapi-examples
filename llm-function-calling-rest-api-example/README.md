Source code for the article [LLM Function Calling with a REST API](https://restfulapi.net/llm-function-calling-rest-api/)

A small Orders REST API (FastAPI), a function calling loop that talks to any
OpenAI-compatible Chat Completions endpoint, and a local stub model server that
returns fixed tool calls for the demo prompts, so everything runs without an API key.

## Versions

- Python 3.13
- fastapi 0.142.2, uvicorn 0.54.0, pydantic 2.13.5
- httpx 0.28.1, jsonschema 4.26.0

## Files

| File | What it does |
|---|---|
| orders_api.py | Orders REST API: GET /orders/{id}, GET /orders/{id}/shipment (limited to 2 calls per 30 s), POST /orders/{id}/cancel (needs an Idempotency-Key header; the first cancel of order 1005 answers after 6 s to show a timeout retry) |
| tools.py | Tool definitions (JSON Schema) and the allow list of HTTP operations |
| executor.py | Validates arguments, asks before writes, calls the API with a 5 s timeout and one retry (same Idempotency-Key) and maps HTTP status codes to tool results |
| agent.py | The loop: model request, tool calls, tool results, final answer |
| stub_model.py | Local stand-in for a Chat Completions endpoint. It is not a language model: it matches the demo prompts with regular expressions and builds answers from templates |
| openapi_tools.py | Builds a tool definition from one OpenAPI operation |
| run_demo.sh | Runs all demo prompts |
| OUTPUTS.txt | Output of one run against the stub |

## Run against the local stub

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn orders_api:app --port 8780 &
uvicorn stub_model:app --port 8781 &

python agent.py --trace "What is the status of order 1001?"
python agent.py "Where are the parcels for orders 1001, 1002 and 1003?"
echo y | python agent.py "Cancel order 1002, wrong size"
./run_demo.sh
```

On Windows, start each uvicorn command in its own terminal instead of using &.
Without LLM_BASE_URL the client uses the stub at http://127.0.0.1:8781/v1.

Restart orders_api to reset the data and the rate limit window.

## Run against a real provider

The client reads three environment variables. Any endpoint that accepts the
Chat Completions request format with the tools field works.

```
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=<your key>
export LLM_MODEL=<a model id that supports tool calling in Chat Completions>
python agent.py --trace "What is the status of order 1001?"
```

With a real model the tool calls and the final wording can differ from the stub run.
