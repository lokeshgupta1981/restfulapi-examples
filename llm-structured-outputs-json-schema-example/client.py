"""Ask an LLM API for calendar events as JSON that matches events_schema.json.

The client builds the structured output request for OpenAI, Anthropic or
Gemini, reads the reply in the vendor's response shape, stops on a refusal or
a truncated answer, and validates the JSON with a JSON Schema validator.

  python client.py openai                      # stub on http://localhost:8000
  python client.py anthropic --max-tokens 30   # truncated answer
  python client.py openai --scenario refusal   # stub test hook

Real API: set LLM_BASE_URL and the vendor's key, for example
  LLM_BASE_URL=https://api.openai.com OPENAI_API_KEY=... python client.py openai
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

from jsonschema import Draft202012Validator

SCHEMA = json.loads(pathlib.Path(__file__).with_name("events_schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)

INSTRUCTIONS = ("Extract every calendar event from the email. Use ISO dates. "
                "Set start_time to null when the email gives no time.")
EMAIL = ("Hi team, the sprint review moves to 2026-10-14 at 15:00 with Ana and Raj. "
         "The budget call with Mei is on 2026-10-16, time to be confirmed. "
         "Please send the Q3 report by 2026-10-20.")

# Example model names from each vendor's structured outputs guide. Override with LLM_MODEL.
VENDORS = {
    "openai": {"path": "/v1/responses", "model": "gpt-6-astra", "key": "OPENAI_API_KEY"},
    "anthropic": {"path": "/v1/messages", "model": "claude-opus-5-5", "key": "ANTHROPIC_API_KEY"},
    "gemini": {"path": "/v1beta/interactions", "model": "gemini-3.8-flash", "key": "GEMINI_API_KEY"},
}


class ModelRefused(Exception):
    """The model declined the request, so the reply does not follow the schema."""


class OutputTruncated(Exception):
    """The token limit cut the answer off, so the JSON is incomplete."""


class InvalidOutput(Exception):
    """The reply is not JSON, breaks the schema, or fails a business check."""


def build_request(vendor: str, model: str, max_tokens: int) -> tuple[dict, dict]:
    """Return (headers, body) in the vendor's request format."""
    key = os.environ.get(VENDORS[vendor]["key"], "stub-key")
    if vendor == "openai":
        headers = {"Authorization": f"Bearer {key}"}
        body = {
            "model": model,
            "input": [{"role": "system", "content": INSTRUCTIONS},
                      {"role": "user", "content": EMAIL}],
            "max_output_tokens": max_tokens,
            "text": {"format": {"type": "json_schema", "name": "calendar_events",
                                "strict": True, "schema": SCHEMA}},
        }
    elif vendor == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": INSTRUCTIONS,
            "messages": [{"role": "user", "content": EMAIL}],
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
        }
    else:
        headers = {"x-goog-api-key": key}
        body = {
            "model": model,
            "system_instruction": INSTRUCTIONS,
            "input": EMAIL,
            "generation_config": {"max_output_tokens": max_tokens},
            "response_format": {"type": "text", "mime_type": "application/json", "schema": SCHEMA},
        }
    return headers, body


def read_reply(vendor: str, data: dict) -> tuple[str, str]:
    """Return (state, text). The state is "done", "refused" or "truncated"."""
    if vendor == "openai":
        message = next(item for item in data["output"] if item["type"] == "message")
        part = message["content"][0]
        if part["type"] == "refusal":
            return "refused", part["refusal"]
        state = "truncated" if data["status"] == "incomplete" else "done"
        return state, part["text"]
    if vendor == "anthropic":
        text = "".join(block["text"] for block in data["content"] if block["type"] == "text")
        states = {"refusal": "refused", "max_tokens": "truncated"}
        return states.get(data["stop_reason"], "done"), text
    # Gemini Interactions API
    if data["status"] not in ("completed", "incomplete"):
        raise InvalidOutput([f"interaction status {data['status']}"])
    outputs = [step for step in data["steps"] if step["type"] == "model_output"]
    text = "".join(part["text"] for part in outputs[-1]["content"] if part["type"] == "text")
    return ("truncated" if data["status"] == "incomplete" else "done"), text


def parse_and_validate(text: str) -> dict:
    """Parse the JSON text, validate it against the schema, then run business checks."""
    try:
        result = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidOutput([f"not valid JSON: {error}"])
    problems = [f"{error.json_path}: {error.message}" for error in VALIDATOR.iter_errors(result)]
    if problems:
        raise InvalidOutput(sorted(problems))
    # Schema-valid is not the same as correct: every date must appear in the email.
    invented = [event["date"] for event in result["events"] if event["date"] not in EMAIL]
    if invented:
        raise InvalidOutput([f"date not found in the email: {date}" for date in invented])
    return result


def extract_events(vendor: str, max_tokens: int = 1024, scenario: str | None = None,
                   show_response: bool = False) -> dict:
    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:8000")
    model = os.environ.get("LLM_MODEL", VENDORS[vendor]["model"])
    headers, body = build_request(vendor, model, max_tokens)
    headers["Content-Type"] = "application/json"
    if scenario:
        headers["X-Stub-Scenario"] = scenario  # test hook of the local stub only
    request = urllib.request.Request(base_url + VENDORS[vendor]["path"],
                                     data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read())
    if show_response:
        print("response:", json.dumps(data))
    state, text = read_reply(vendor, data)
    if state == "refused":
        raise ModelRefused(text)
    if state == "truncated":
        # Check the stop reason before parsing: the cut-off text is not valid JSON.
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            raise OutputTruncated(f"{len(text)} characters received, json.loads says: {error}")
        raise OutputTruncated(f"{len(text)} characters received")
    return parse_and_validate(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor", choices=VENDORS)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--scenario", choices=["refusal", "drift", "wrong-date"])
    parser.add_argument("--show-response", action="store_true")
    args = parser.parse_args()
    try:
        events = extract_events(args.vendor, args.max_tokens, args.scenario, args.show_response)
    except ModelRefused as error:
        print(f"REFUSED: {error}")
        return 2
    except OutputTruncated as error:
        print(f"TRUNCATED: {error}. Retry with a higher token limit.")
        return 3
    except InvalidOutput as error:
        print("INVALID:")
        for problem in error.args[0]:
            print(f"  {problem}")
        return 4
    except urllib.error.HTTPError as error:
        print(f"HTTP {error.code}: {error.read().decode()}")
        return 5
    print(json.dumps(events, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
