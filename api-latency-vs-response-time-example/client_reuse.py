"""Call the Orders API 20 times, first with a new connection for every call,
then with one reused client, and print the median response time of each.

Start server.py --tls and delay_proxy.py first (or run demo.sh).
Run: python3 client_reuse.py [--url https://localhost:9201/orders/42] [-n 20]
"""
import argparse
import ssl
import statistics
import time

import httpx


def timed_calls(n, call):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        response = call()
        response.raise_for_status()
        times.append((time.perf_counter() - start) * 1000)
    return times


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://localhost:9201/orders/42")
    parser.add_argument("-n", type=int, default=20)
    parser.add_argument("--cacert", default="cert.pem")
    args = parser.parse_args()
    tls = ssl.create_default_context(cafile=args.cacert)

    # Wrong: httpx.get() opens a new TCP and TLS connection on every call
    new_each_time = timed_calls(args.n, lambda: httpx.get(args.url, verify=tls))

    # Right: one Client keeps the connection open and reuses it
    with httpx.Client(verify=tls) as client:
        reused = timed_calls(args.n, lambda: client.get(args.url))

    print(f"{args.n} calls to {args.url}")
    print(f"httpx.get() each time : median {statistics.median(new_each_time):6.1f} ms")
    print(f"one httpx.Client      : median {statistics.median(reused):6.1f} ms")


if __name__ == "__main__":
    main()
