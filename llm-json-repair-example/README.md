Source code for the article [How to Fix Invalid JSON from an LLM](https://restfulapi.net/fix-invalid-json-from-llm/)

# LLM JSON repair example

A parse, repair and validate pipeline for model replies that should hold an order as JSON, tested on 11 broken replies.

- `broken_outputs.py` holds the test replies: a valid one, a Markdown fence, prose around the JSON, a trailing comma, single quotes, Python literals, comments, unquoted keys, an unescaped quote, a truncated reply and a `NaN` value.
- `llm_json.py` is the pipeline. `parse_reply(text, finish_reason)` tries `json.loads` first, extracts the JSON from fences and prose, repairs it with json-repair, rejects `NaN` and `Infinity`, and validates the result with a Pydantic model. It returns `valid`, `repaired` or `retry` (for a truncated reply or a schema error), and `retry_prompt()` builds the follow-up message with the error.
- `demo.py` runs every reply through the pipeline and shows one retry with a stub model.
- `js/repair.mjs` runs the same replies through jsonrepair and a Zod schema in Node.js, for comparison.

No model API is called, so no API key is needed. To use a real model, pass its reply text and its stop reason to `parse_reply`. With OpenAI Chat Completions, pass `finish_reason`. With the OpenAI Responses API, pass `length` when `incomplete_details.reason` is `max_output_tokens`. With the Anthropic Messages API, pass `length` when `stop_reason` is `max_tokens` or `model_context_window_exceeded`.

## Versions

Python 3.13, json-repair 0.64.0, Pydantic 2.14.0. Node.js 22, jsonrepair 3.15.0, Zod 4.6.5.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate, and run the script in Git Bash or WSL
pip install -r requirements.txt
./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run.
