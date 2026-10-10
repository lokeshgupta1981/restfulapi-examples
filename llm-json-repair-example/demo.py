"""Runs every broken reply through the pipeline, then shows one retry with a stub model."""

import json

import json_repair
from broken_outputs import CASES
from llm_json import parse_reply, retry_prompt

print(f"{'case':<20} {'json.loads':<11} {'outcome':<9} detail")
for name, text in CASES.items():
    try:
        json.loads(text)
        strict = "ok"
    except json.JSONDecodeError:
        strict = "error"
    finish_reason = "length" if name == "truncated output" else "stop"
    result = parse_reply(text, finish_reason)
    detail = result.reason if result.outcome == "retry" else f"total={result.order.total} items={len(result.order.items)}"
    print(f"{name:<20} {strict:<11} {result.outcome:<9} {detail}")

print("\n== The truncated reply without the stop reason check")
print("json_repair.loads on the raw reply:", json.dumps(json_repair.loads(CASES["truncated output"])))
print("pipeline result:", parse_reply(CASES["truncated output"], "stop").reason)

print("\n== Retry with the reason")
first = parse_reply(CASES["NaN value"])
print("prompt:", retry_prompt(first.reason))
stub_reply = '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2}], "total": 59.9, "currency": "EUR"}'
second = parse_reply(stub_reply)
print("second reply:", second.outcome, second.order.model_dump(exclude_defaults=True))
