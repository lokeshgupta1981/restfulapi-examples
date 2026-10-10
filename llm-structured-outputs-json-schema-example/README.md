Source code for the article [LLM Structured Outputs with JSON Schema](https://restfulapi.net/llm-structured-outputs-json-schema/)

# LLM structured outputs example

A Python client that asks an LLM API for the calendar events in an email and gets them back as JSON that matches a JSON Schema (`events_schema.json`). The same client speaks three request formats:

- OpenAI Responses API: `POST /v1/responses` with `text.format` set to `{"type": "json_schema", "strict": true, "schema": ...}`
- Anthropic Messages API: `POST /v1/messages` with `output_config.format` set to `{"type": "json_schema", "schema": ...}`
- Gemini Interactions API: `POST /v1beta/interactions` with `response_format` set to `{"type": "text", "mime_type": "application/json", "schema": ...}`

The client reads the reply in each vendor's response shape and then:

- stops on a refusal (OpenAI `refusal` content part, Anthropic `stop_reason: "refusal"`),
- stops on a truncated answer (OpenAI and Gemini `status: "incomplete"`, Anthropic `stop_reason: "max_tokens"`) before it parses the JSON,
- parses the JSON and validates it with `jsonschema` (Draft 2020-12, with format checking), and
- runs a business check: every extracted date must appear in the email.

No API key is needed. `stub_server.py` is a local FastAPI app that accepts the three request formats and answers in the documented response shapes. There is no model behind it: a few regular expressions extract the events. The request header `X-Stub-Scenario` (`refusal`, `drift`, `wrong-date`) and a low token limit trigger the failure cases. The stub counts 4 characters as one token.

## Files

- `events_schema.json`: the JSON Schema that the client sends and validates against.
- `client.py`: builds the request for each vendor, reads the reply, validates it.
- `stub_server.py`: local stand-in for the three APIs.
- `run_demo.sh`: runs every case (finished answer, truncation, refusal, schema drift, wrong date).
- `OUTPUTS.txt`: output of `run_demo.sh` from a real run.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0 (stub only), jsonschema 4.26.0 (pinned in `requirements.txt`)
- The client uses only `jsonschema` and the Python standard library.

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/llm-structured-outputs-json-schema-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn stub_server:app --port 8000      # terminal 1
./run_demo.sh                            # terminal 2 (Windows: Git Bash or WSL)
python client.py gemini --max-tokens 30  # or run a single case
```

## Use a real API

Set `LLM_BASE_URL` to the vendor's API host and the vendor's key variable. `LLM_MODEL` overrides the example model name in `client.py`. The `X-Stub-Scenario` header is only sent with `--scenario`, so do not use that option against a real API.

```bash
LLM_BASE_URL=https://api.openai.com OPENAI_API_KEY=... python client.py openai
LLM_BASE_URL=https://api.anthropic.com ANTHROPIC_API_KEY=... python client.py anthropic
LLM_BASE_URL=https://generativelanguage.googleapis.com GEMINI_API_KEY=... python client.py gemini
```

Real calls cost money and the model's answer differs from the stub's answer. Check the vendor's model list for a current model name.
