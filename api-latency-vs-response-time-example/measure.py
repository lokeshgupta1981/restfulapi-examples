"""Send N requests to the Orders API and print latency percentiles.

For every request the script records:
  connect   TCP connect plus TLS handshake (0 when the connection is reused)
  wait      from sending the request until the status line and headers arrive
            (curl: time_starttransfer minus time_pretransfer)
  server    the total;dur value from the Server-Timing response header
  network   wait minus server: time on the wire and in proxies, both ways
  total     from the start of the request until the last body byte arrives,
            including connect (curl: time_total)

Run: python3 measure.py [--url https://localhost:9201/orders/42] [-n 500]
     [--new-connection] [--csv results.csv]
"""
import argparse
import csv
import http.client
import math
import ssl
import statistics
import time
from urllib.parse import urlsplit


def percentile(sorted_values, p):
    """Nearest-rank percentile: the smallest value that p% of samples are <= to."""
    rank = math.ceil(p / 100 * len(sorted_values))
    return sorted_values[max(rank, 1) - 1]


def server_total_ms(header_value):
    """Read 'total;dur=12.3' out of a Server-Timing header value."""
    for metric in (header_value or "").split(","):
        parts = [part.strip() for part in metric.split(";")]
        if parts[0] == "total":
            for param in parts[1:]:
                if param.startswith("dur="):
                    return float(param[4:])
    return None


def open_connection(url, context):
    if url.scheme == "https":
        return http.client.HTTPSConnection(url.hostname, url.port, context=context)
    return http.client.HTTPConnection(url.hostname, url.port)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://localhost:9201/orders/42")
    parser.add_argument("-n", type=int, default=500)
    parser.add_argument("--new-connection", action="store_true",
                        help="open a new connection for every request")
    parser.add_argument("--cacert", default="cert.pem")
    parser.add_argument("--csv", help="write one row per request to this file")
    args = parser.parse_args()

    url = urlsplit(args.url)
    context = ssl.create_default_context(cafile=args.cacert)
    rows = []
    connection = None

    for i in range(args.n):
        start = time.perf_counter()
        if connection is None or args.new_connection:
            connection = open_connection(url, context)
            connection.connect()  # TCP connect, plus the TLS handshake for https
        connected = time.perf_counter()

        connection.request("GET", url.path)
        response = connection.getresponse()  # returns once the headers are in
        first_byte = time.perf_counter()
        response.read()
        done = time.perf_counter()
        if args.new_connection:
            connection.close()

        wait_ms = (first_byte - connected) * 1000
        server_ms = server_total_ms(response.getheader("Server-Timing"))
        rows.append({
            "request": i + 1,
            "status": response.status,
            "connect_ms": round((connected - start) * 1000, 2),
            "wait_ms": round(wait_ms, 2),
            "total_ms": round((done - start) * 1000, 2),
            "server_ms": server_ms,
            "network_ms": round(wait_ms - server_ms, 2) if server_ms is not None else None,
        })

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    statuses = sorted({row["status"] for row in rows})
    mode = "new connection per request" if args.new_connection else "one reused connection"
    print(f"{len(rows)} requests to {args.url} ({mode}), statuses {statuses}")
    print(f"{'metric (ms)':<12}{'mean':>8}{'p50':>8}{'p90':>8}{'p95':>8}{'p99':>8}{'max':>8}")
    for key in ["connect_ms", "wait_ms", "server_ms", "network_ms", "total_ms"]:
        values = sorted(row[key] for row in rows if row[key] is not None)
        cells = [statistics.fmean(values)] + [percentile(values, p) for p in (50, 90, 95, 99)] + [values[-1]]
        print(f"{key[:-3]:<12}" + "".join(f"{cell:>8.1f}" for cell in cells))

    totals = [row["total_ms"] for row in rows]
    mean_total = statistics.fmean(totals)
    above_mean = sum(1 for t in totals if t > mean_total)
    print(f"requests slower than the mean: {above_mean} of {len(totals)}")


if __name__ == "__main__":
    main()
