# Token-based rate limiting for LLM APIs: working example

Companion code for the article [Token-Based Rate Limiting for LLM and AI Agent APIs](https://restfulapi.net/token-based-rate-limiting-llm-apis/) on restfulapi.net.
Tested on 2026-10-02 with Python 3.11, Redis 7.0.15 and the versions in requirements.txt.

## Files
- fake_llm.py: stand-in for an LLM provider (OpenAI-style Chat Completions, real token counts with tiktoken), so no API key is needed
- gateway.py: REST API gateway with a token bucket per API key in Redis; reserves tokens before the call and refunds unused ones after
- agent_client.py: simulates an AI agent that sends parallel calls and obeys Retry-After

## Run
    git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
    cd restfulapi-examples/token-based-rate-limiting-example
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

    # Redis 7 or newer on localhost:6379. Install it from https://redis.io/docs/latest/operate/oss_and_stack/install/
    # (on Windows use WSL or Docker), then start it without saving to disk:
    redis-server --port 6379 --save ""

    # Terminal 2: fake LLM on port 9000
    uvicorn fake_llm:app --port 9000

    # Terminal 3 and 4: two gateway instances that share one budget
    uvicorn gateway:app --port 8080
    uvicorn gateway:app --port 8081

    # Try it
    curl -i localhost:8080/v1/chat/completions -H 'Authorization: Bearer key-free' \
      -H 'Content-Type: application/json' \
      -d '{"messages":[{"role":"user","content":"Summarize the open orders."}],"max_tokens":500}'
    python agent_client.py 6

To use a real provider, set UPSTREAM_URL to its base URL without the /v1 part (for example https://api.openai.com) and add your provider API key as an Authorization header on the upstream client in gateway.py.
