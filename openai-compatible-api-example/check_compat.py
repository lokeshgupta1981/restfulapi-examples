"""Checks how closely a server follows the OpenAI Chat Completions wire format.

It uses the official OpenAI Python SDK, so every check also proves that the SDK can parse
the server's responses. Point it at any server with three environment variables:

  OPENAI_BASE_URL  for example http://127.0.0.1:8000/v1 or http://localhost:11434/v1
  OPENAI_API_KEY   the key for that server
  MODEL            a model id that the server knows
"""

import json
import os
import time
import urllib.request

import openai
from openai import OpenAI

BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "demo-key")
MODEL = os.getenv("MODEL", "echo-1")
BURST_KEY = os.getenv("BURST_KEY")  # a second key for the rate-limit check, which sends up to 21 requests

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
results = []


def check(name):
    def wrap(fn):
        try:
            status, detail = fn()
        except Exception as exc:  # any exception is a failed check, with its type and message
            status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
        results.append((status, name, detail))
        print(f"{status:<5} {name:<34} {detail}")
        return fn
    return wrap


print(f"Checking {BASE_URL} with model {MODEL}\n")


@check("GET /models lists the model")
def models():
    ids = [m.id for m in client.models.list()]
    return ("PASS" if MODEL in ids else "FAIL"), f"{len(ids)} models: {', '.join(ids[:4])}"


@check("POST /chat/completions")
def basic():
    completion = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": "hello"}])
    choice = completion.choices[0]
    ok = completion.object == "chat.completion" and choice.message.role == "assistant" and choice.finish_reason
    usage = completion.usage.total_tokens if completion.usage else None
    return ("PASS" if ok else "FAIL"), f"finish_reason={choice.finish_reason}, total_tokens={usage}"


@check("stream returns text chunks")
def stream():
    pieces, finish = [], None
    for chunk in client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": "hello"}],
                                                stream=True):
        if chunk.choices:
            pieces.append(chunk.choices[0].delta.content or "")
            finish = chunk.choices[0].finish_reason or finish
    return ("PASS" if finish and pieces else "FAIL"), f"{len(pieces)} chunks, text={''.join(pieces)!r}"


@check("raw stream ends with data: [DONE]")
def raw_done():
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions", method="POST",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        data=json.dumps({"model": MODEL, "stream": True,
                         "messages": [{"role": "user", "content": "hello"}]}).encode())
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "")
        lines = [line.decode().strip() for line in response if line.strip()]
    ok = lines[-1] == "data: [DONE]" and content_type.startswith("text/event-stream")
    return ("PASS" if ok else "FAIL"), f"Content-Type={content_type.split(';')[0]}, last line={lines[-1]!r}"


@check("stream_options.include_usage")
def stream_usage():
    last = None
    for chunk in client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": "hello"}],
                                                stream=True, stream_options={"include_usage": True}):
        last = chunk
    if last is None or last.usage is None:
        return "WARN", "no usage in the last chunk"
    shape = "empty choices (OpenAI shape)" if not last.choices else "non-empty choices"
    return "PASS", f"usage in last chunk, {shape}, total_tokens={last.usage.total_tokens}"


@check("unknown model returns 404")
def unknown_model():
    try:
        client.chat.completions.create(model="no-such-model", messages=[{"role": "user", "content": "hi"}])
    except openai.NotFoundError as exc:
        return "PASS", f"NotFoundError, code={exc.code}, param={exc.param}"
    return "FAIL", "the server answered with a model that does not exist"


@check("bad API key returns 401")
def bad_key():
    try:
        OpenAI(base_url=BASE_URL, api_key="wrong-key").models.list()
    except openai.AuthenticationError as exc:
        return "PASS", f"AuthenticationError, code={exc.code}"
    return "WARN", "the server accepts any key"


@check("unsupported n=2 is reported")
def unsupported_param():
    try:
        completion = client.chat.completions.create(model=MODEL, n=2, messages=[{"role": "user", "content": "hi"}])
    except openai.BadRequestError as exc:
        return "PASS", f"BadRequestError, param={exc.param}, message={exc.body['message']!r}"
    return "WARN", f"accepted and returned {len(completion.choices)} choice(s), the parameter was ignored"


@check("429 has Retry-After, SDK retries")
def rate_limit():
    if not BURST_KEY:
        return "SKIP", "set BURST_KEY to a second valid key to run this check"
    no_retry = OpenAI(base_url=BASE_URL, api_key=BURST_KEY, max_retries=0)
    messages = [{"role": "user", "content": "hi"}]
    try:
        for _ in range(20):
            no_retry.chat.completions.create(model=MODEL, messages=messages)
        return "WARN", "no HTTP 429 after 20 requests"
    except openai.RateLimitError as exc:
        retry_after = exc.response.headers.get("retry-after")
        remaining = exc.response.headers.get("x-ratelimit-remaining-requests")
    started = time.time()
    OpenAI(base_url=BASE_URL, api_key=BURST_KEY).chat.completions.create(model=MODEL, messages=messages)
    waited = time.time() - started
    return "PASS", f"Retry-After={retry_after}, remaining={remaining}, retried call succeeded after {waited:.0f}s"


counts = {s: sum(1 for r in results if r[0] == s) for s in ("PASS", "WARN", "FAIL", "SKIP")}
print(f"\n{counts['PASS']} passed, {counts['WARN']} warnings, {counts['FAIL']} failed, {counts['SKIP']} skipped")
