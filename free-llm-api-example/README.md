# Free LLM API example: one client, many free providers

Source code for the article https://restfulapi.net/free-llm-apis/

`free_llm.py` sends a prompt through a list of free LLM API providers with the OpenAI Python SDK. It skips providers without a key, waits out a short `retry-after` on HTTP 429, and moves to the next provider when the daily quota is gone. `mock_provider.py` has two fake OpenAI-compatible providers, so the 429 handling can be tested without any API key.

Free limits change often. Check each provider's limits page before relying on a number.

## Versions

Python 3.10 or later, openai 3.28.0, FastAPI 0.143.0 and Uvicorn 0.54.0 (FastAPI and Uvicorn only for the mock).

## Run against the mock providers

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# terminal 1
uvicorn mock_provider:busy --port 8101
# terminal 2
uvicorn mock_provider:flaky --port 8102
# terminal 3
GROQ_API_KEY=test-key GROQ_BASE_URL=http://127.0.0.1:8101/v1 \
OPENROUTER_API_KEY=test-key OPENROUTER_BASE_URL=http://127.0.0.1:8102/v1 \
python free_llm.py
```

Expected output:

```text
gemini: skipped, GEMINI_API_KEY is not set
groq: HTTP 429 on attempt 1, retry-after 3600 s
openrouter: HTTP 429 on attempt 1, retry-after 2 s
openrouter: HTTP 200 on attempt 2, 21 tokens
answer from openrouter: HTTP 429 means the client sent too many requests.
```

Restart the `flaky` mock before running again, because it returns HTTP 429 only for its first request.

## Run against real providers

Set one or more keys and leave the `*_BASE_URL` variables unset: `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`. For a local Ollama server, pull the model (`ollama pull llama3.2`) and set `OLLAMA_API_KEY` to any value, since Ollama ignores it.

```bash
python free_llm.py "Explain HTTP 429 in one sentence."
```

Keep keys in environment variables or a `.env` file that is not committed.
