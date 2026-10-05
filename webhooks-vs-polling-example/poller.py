"""Polling client: asks the change feed for new events on a fixed interval.

Sends If-None-Match with the last ETag, so an unchanged feed costs an
HTTP 304 with no body. Writes its measurements to a JSON file.
"""
import argparse
import json
import time
import urllib.error
import urllib.request


def poll_once(base_url, after, etag):
    request = urllib.request.Request(f"{base_url}/events?after={after}")
    if etag:
        request.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read()
            return response.status, response.headers.get("ETag"), body
    except urllib.error.HTTPError as error:
        if error.code == 304:
            return 304, etag, b""
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="http://127.0.0.1:9140")
    parser.add_argument("--interval", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--no-etag", action="store_true", help="do not send If-None-Match")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    after, etag = 0, None
    requests, responses_304, responses_200_new, body_bytes = 0, 0, 0, 0
    delays = []
    end = time.time() + args.duration
    while time.time() < end:
        status, new_etag, body = poll_once(args.provider, after, None if args.no_etag else etag)
        requests += 1
        body_bytes += len(body)
        if status == 304:
            responses_304 += 1
        else:
            etag = new_etag
            page = json.loads(body)
            if page["events"]:
                responses_200_new += 1
            now = time.time()
            for event in page["events"]:
                delays.append(now - event["created_ts"])
            after = page["next_after"]
        time.sleep (args.interval)

    result = {
        "mode": f"poll every {args.interval:g} s" + (" (no ETag)" if args.no_etag else ""),
        "requests": requests,
        "responses_with_new_events": responses_200_new,
        "responses_304": responses_304,
        "events_seen": len(delays),
        "body_bytes": body_bytes,
        "delays": delays,
    }
    with open(args.out, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
