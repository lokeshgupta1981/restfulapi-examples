"""Python client for POST /v1/answers/stream with a small SSE parser.

Usage:
  python client.py "What are server-sent events?"
  python client.py "What are server-sent events?" --stop-after 10
  python client.py "Explain SSE" --url http://127.0.0.1:9380/buffered/v1/answers/stream
"""
import argparse
import json
import time

import httpx


def parse_sse(lines):
    # Collect fields until a blank line, then yield one event (WHATWG rules, simplified).
    event, data, event_id = "message", [], None
    for line in lines:
        if line == "":
            if data:
                yield {"event": event, "data": "\n".join(data), "id": event_id}
            event, data = "message", []
            continue
        if line.startswith(":"):
            yield {"event": "comment", "data": line[1:].strip(), "id": None}
            continue
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            event = value
        elif field == "data":
            data.append(value)
        elif field == "id":
            event_id = value


def main():
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--url", default="http://127.0.0.1:9300/v1/answers/stream")
    p.add_argument("--model", default="fake-model")
    p.add_argument("--stop-after", type=int, default=0, help="disconnect after N tokens")
    args = p.parse_args()

    start = time.monotonic()
    ms = lambda: round((time.monotonic() - start) * 1000)
    first = {}
    tokens = 0
    finished = False
    body = {"question": args.question, "model": args.model}
    with httpx.stream("POST", args.url, json=body, timeout=60) as resp:
        print(f"[{ms():5d} ms] HTTP {resp.status_code} {resp.headers.get('content-type')}")
        if resp.status_code != 200:
            print(resp.read().decode())
            return
        for ev in parse_sse(resp.iter_lines()):
            first.setdefault(ev["event"], ms())
            if ev["event"] == "comment":
                print(f"[{ms():5d} ms] (heartbeat: {ev['data']})")
            elif ev["event"] == "token":
                tokens += 1
                print(json.loads(ev["data"])["text"], end="", flush=True)
                if tokens == args.stop_after:
                    print(f"\n[{ms():5d} ms] stopping after {tokens} tokens (closing the connection)")
                    return
            elif ev["event"] in ("done", "error"):
                print(f"\n[{ms():5d} ms] {ev['event']}: {ev['data']}")
                finished = True
    if not finished:
        print(f"\n[{ms():5d} ms] incomplete: the stream closed without a done or error event")
    print(f"first token at {first.get('token')} ms, last event at {ms()} ms, {tokens} token events")


if __name__ == "__main__":
    main()
