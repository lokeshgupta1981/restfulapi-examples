"""Runs the two scenarios and prints the measured numbers.

Scenario 1 (steady): one provider emits 30 events. Three polling clients
(every 1 s, 5 s and 15 s, with ETag), one polling client without ETag
(every 5 s) and one webhook receiver all watch the same event stream.

Scenario 2 (outage): the webhook receiver answers HTTP 503 for 21 s, the
provider retries each event 3 times (after 1 s, 2 s, 4 s) and gives up,
and the receiver's reconciliation poll (every 20 s) finds the lost events.
"""
import json
import math
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PY = sys.executable
HERE = Path(__file__).parent
RESULTS = HERE / "results"
PROVIDER = "http://127.0.0.1:9140"
HOOK_URL = "http://127.0.0.1:9141/webhooks/orders"


def start(*args):
    return subprocess.Popen([PY, *args], cwd=HERE)


def stats():
    with urllib.request.urlopen(f"{PROVIDER}/stats") as response:
        return json.loads(response.read())


def p95(values):
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def line(row):
    print("{:<26}{:>9}{:>11}{:>7}{:>8}{:>11}{:>11}{:>11}".format(*row))


def summary(result):
    d = result["delays"]
    all_delays = d if isinstance(d, list) else d["webhook"] + d["reconcile"]
    requests = result.get("requests", result.get("posts"))
    useful = result.get("responses_with_new_events", result["events_seen"])
    return [
        result["mode"],
        requests,
        useful,
        requests - useful,
        result["events_seen"],
        f"{sum(all_delays) / len(all_delays):.2f} s",
        f"{p95(all_delays):.2f} s",
        f"{max(all_delays):.2f} s",
    ]


def steady():
    print("== Scenario 1: same 30 events, polling vs webhooks ==", flush=True)
    receiver = start("receiver.py", "--duration", "75", "--out", str(RESULTS / "webhook.json"))
    time.sleep (0.5)
    provider = start("provider.py", "--webhook-url", HOOK_URL)
    time.sleep (0.5)
    pollers = [
        start("poller.py", "--interval", "1", "--duration", "75", "--out", str(RESULTS / "poll-1.json")),
        start("poller.py", "--interval", "5", "--duration", "75", "--out", str(RESULTS / "poll-5.json")),
        start("poller.py", "--interval", "15", "--duration", "75", "--out", str(RESULTS / "poll-15.json")),
        start("poller.py", "--interval", "5", "--no-etag", "--duration", "75",
              "--out", str(RESULTS / "poll-5-no-etag.json")),
    ]
    for process in [receiver, *pollers]:
        process.wait()
    provider_stats = stats()
    provider.terminate()
    provider.wait()

    print()
    line(["client", "requests", "with news", "empty", "events", "avg delay", "p95 delay", "max delay"])
    extra = []
    for name in ["poll-1", "poll-5", "poll-15", "poll-5-no-etag", "webhook"]:
        result = json.loads((RESULTS / f"{name}.json").read_text())
        line(summary(result))
        if "responses_304" in result:
            extra.append(f"{result['mode']}: {result['responses_304']} of the empty answers were HTTP 304")
    print()
    print("\n".join(extra))
    print("provider:", json.dumps({k: provider_stats[k] for k in
                                   ["events", "feed_requests", "feed_200", "feed_200_empty", "feed_304",
                                    "webhook_attempts", "webhook_delivered"]}))


def outage():
    print("\n== Scenario 2: receiver down for 21 s, hybrid pattern ==", flush=True)
    receiver = start("receiver.py", "--outage", "15:36", "--reconcile-every", "20", "--duration", "80",
                     "--out", str(RESULTS / "hybrid.json"))
    time.sleep (0.5)
    provider = start("provider.py", "--webhook-url", HOOK_URL, "--retry", "1,2,4")
    receiver.wait()
    provider_stats = stats()
    provider.terminate()
    provider.wait()

    result = json.loads((RESULTS / "hybrid.json").read_text())
    by_webhook, by_reconcile = result["delays"]["webhook"], result["delays"]["reconcile"]
    print()
    print(f"events published:            {provider_stats['events']}")
    print(f"webhook POST attempts:       {provider_stats['webhook_attempts']}"
          f" (HTTP 503 answers: {result['rejected_503']})")
    print(f"delivered by webhook:        {len(by_webhook)}")
    print(f"dead-lettered by provider:   {provider_stats['webhook_dead_lettered']} {provider_stats['dead_letter']}")
    print(f"recovered by reconciliation: {len(by_reconcile)}")
    print(f"duplicate webhooks dropped:  {result['duplicates']}")
    print(f"events processed in total:   {result['events_seen']} of {provider_stats['events']}")
    print(f"reconcile requests:          {result['reconcile_requests']}")
    if by_reconcile:
        print(f"delay of recovered events:   avg {sum(by_reconcile) / len(by_reconcile):.1f} s,"
              f" max {max(by_reconcile):.1f} s")


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    steady()
    outage()
