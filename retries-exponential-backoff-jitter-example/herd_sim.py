"""Simulates 100 clients that retry against a server that is down for 1 second.

After the outage the server can answer 10 requests per 100 ms and rejects the rest with 503.
Every client sends its first request at t = 0. Each round trip takes 5 to 15 ms.
Usage: python herd_sim.py [runs]   (each run uses its own random seed, so results repeat)
"""
import heapq
import json
import random
import statistics
import sys

CLIENTS, DOWN_MS, CAPACITY, WINDOW_MS = 100, 1000, 10, 100
BASE_MS, CAP_MS, MAX_ATTEMPTS = 100, 5000, 30

STRATEGIES = {
    "fixed 100 ms":             lambda attempt, rnd: BASE_MS,
    "exponential, no jitter":   lambda attempt, rnd: min(CAP_MS, BASE_MS * 2 ** attempt),
    "exponential, full jitter": lambda attempt, rnd: rnd.uniform(0, min(CAP_MS, BASE_MS * 2 ** attempt)),
}


def simulate(delay, seed: int) -> dict:
    rnd = random.Random(seed)
    queue = [(0.0, client, 0) for client in range(CLIENTS)]   # (send time ms, client, attempt)
    heapq.heapify(queue)
    served, per_window, last_ok, failed = {}, {}, 0.0, 0
    while queue:
        t, client, attempt = heapq.heappop(queue)
        window = int(t // WINDOW_MS)
        per_window[window] = per_window.get(window, 0) + 1
        ok = t >= DOWN_MS and served.get(window, 0) < CAPACITY
        if ok:
            served[window] = served.get(window, 0) + 1
            last_ok = max(last_ok, t)
        elif attempt + 1 < MAX_ATTEMPTS:
            rtt = rnd.uniform(5, 15)
            heapq.heappush(queue, (t + rtt + delay(attempt, rnd), client, attempt + 1))
        else:
            failed += 1
    return {"requests": sum(per_window.values()), "failed_clients": failed,
            "all_done_ms": round(last_ok),
            "peak_after_outage": max(n for w, n in per_window.items() if w * WINDOW_MS >= DOWN_MS),
            "per_window": per_window}


def main(runs: int) -> None:
    print(f"{CLIENTS} clients, server down {DOWN_MS} ms, then {CAPACITY} requests per {WINDOW_MS} ms; "
          f"median of {runs} runs")
    print(f"{'strategy':26} {'requests':>8} {'all served (ms)':>15} {'peak per 100 ms after outage':>29}")
    timelines = {}
    for name, delay in STRATEGIES.items():
        rs = [simulate(delay, seed) for seed in range(runs)]
        med = lambda k: statistics.median(r[k] for r in rs)
        print(f"{name:26} {med('requests'):8.0f} {med('all_done_ms'):15.0f} {med('peak_after_outage'):29.0f}"
              f"   clients that gave up: {sum(r['failed_clients'] for r in rs)}")
        timelines[name] = rs[0]["per_window"]                     # seed 0, for the chart
    with open("herd-timeline.json", "w") as f:
        json.dump(timelines, f)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 21)
