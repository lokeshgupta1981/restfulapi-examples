"""Function calling loop against any OpenAI-compatible Chat Completions endpoint.

Environment variables:
  LLM_BASE_URL    default http://127.0.0.1:8781/v1 (the local stub model)
  LLM_API_KEY     default stub-key
  LLM_MODEL       default stub-model
  ORDERS_API_URL  default http://127.0.0.1:8780
"""
import json
import os
import sys

import httpx

from executor import execute_tool_call
from tools import TOOLS

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8781/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "stub-key")
LLM_MODEL = os.environ.get("LLM_MODEL", "stub-model")
ORDERS_API_URL = os.environ.get("ORDERS_API_URL", "http://127.0.0.1:8780")
MAX_ROUNDS = 5
TRACE = "--trace" in sys.argv

SYSTEM_PROMPT = ("You are an order support helper. Use the tools to look up real data. "
                 "Never guess order data. If a tool returns an error, explain it to the user.")


def trace(label: str, payload) -> None:
    if TRACE:
        print(f"--- {label} ---")
        print(json.dumps(payload, indent=2))


def ask_user(name: str, arguments: dict) -> bool:
    answer = input(f"Confirm {name} {json.dumps(arguments)}? [y/N] ")
    if not sys.stdin.isatty():
        print(answer)  # show a piped answer in the log
    return answer.strip().lower() == "y"


def call_model(llm: httpx.Client, messages: list, round_number: int) -> dict:
    request_body = {"model": LLM_MODEL, "messages": messages, "tools": TOOLS, "tool_choice": "auto"}
    shown = dict(request_body)
    if round_number > 0:
        shown["tools"] = f"[{len(TOOLS)} tools, same as round 0]"
    trace(f"round {round_number}: request to model", shown)
    response = llm.post("/chat/completions", json=request_body)
    response.raise_for_status()
    data = response.json()
    trace(f"round {round_number}: response from model", data)
    return data


def run(prompt: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}]
    llm = httpx.Client(base_url=LLM_BASE_URL, timeout=60.0,
                       headers={"Authorization": f"Bearer {LLM_API_KEY}"})
    api = httpx.Client(base_url=ORDERS_API_URL, timeout=httpx.Timeout(5.0))

    for round_number in range(MAX_ROUNDS):
        choice = call_model(llm, messages, round_number)["choices"][0]
        message = choice["message"]
        messages.append(message)  # keep the assistant turn, including its tool_calls

        if choice["finish_reason"] != "tool_calls":
            return message.get("content") or ""

        for call in message["tool_calls"]:
            name = call["function"]["name"]
            print(f"[tool] {name} {call['function']['arguments']}")
            result = execute_tool_call(api, call["id"], name, call["function"]["arguments"], ask_user)
            print(f"[result] {json.dumps(result)}")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})

    return "Stopped: too many tool rounds."


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--trace"]
    answer = run(" ".join(args))
    print(f"[answer] {answer}")
