"""Read a JSON Lines file one line at a time and report bad lines with their line number."""
import json
import sys


def read_jsonl(path, skip_bad=False):
    with open(path, encoding="utf-8") as source:
        for line_no, line in enumerate(source, start=1):
            if not line.strip():
                print(f"line {line_no}: blank line skipped", file=sys.stderr)
                continue
            try:
                yield json.loads(line.rstrip("\r\n"))
            except json.JSONDecodeError as err:
                if not skip_bad:
                    raise ValueError(f"line {line_no}: {err.msg} (column {err.colno})") from err
                print(f"line {line_no}: skipped, {err.msg} (column {err.colno})", file=sys.stderr)


if __name__ == "__main__":
    path = sys.argv[1]
    skip_bad = "--skip-bad" in sys.argv
    paid_total = 0.0
    count = 0
    try:
        for order in read_jsonl(path, skip_bad):
            count += 1
            if order["status"] == "paid":
                paid_total += order["total"]
    except ValueError as err:
        sys.exit(f"stopped: {err}")
    print(f"{count} orders, paid total {paid_total:.2f}")
