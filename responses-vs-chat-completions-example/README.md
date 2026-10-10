Source code for the article [Responses API vs Chat Completions](https://restfulapi.net/responses-api-vs-chat-completions/)

# Responses API vs Chat Completions example

The same order-support conversation in both OpenAI API styles, with the official OpenAI Python SDK. The SDK talks to a local stub server, so no API key is needed.

- `stub_server.py` is a FastAPI stub of `POST /v1/chat/completions` and `POST /v1/responses`. It returns the fields of the OpenAI API reference, stores responses for `previous_response_id`, returns tool calls, and streams in both formats (`chat.completion.chunk` with `data: [DONE]`, and named Responses events). The "model" is a few fixed rules, and token counts are word counts.
- `chat_demo.py` runs a tool call, a follow-up turn with and without the history, and a streamed answer with Chat Completions.
- `responses_demo.py` runs the same steps with the Responses API and `previous_response_id`.
- `wire.sh` sends raw HTTP requests with curl and prints the JSON and the event streams of both APIs.

## Versions

Python 3.13, openai 3.28.0, FastAPI 0.143.0, Uvicorn 0.54.0.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: run the scripts in Git Bash or WSL
pip install -r requirements.txt
./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run.

## Use the OpenAI API instead of the stub

```bash
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...        # your key
export MODEL=<a model name from the OpenAI models page>
python3 chat_demo.py
python3 responses_demo.py
```
