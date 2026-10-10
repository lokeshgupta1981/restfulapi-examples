"""Checks an llms.txt file against the llms.txt proposal and follows every link.

It parses the file with the llms-txt package from Answer.AI (the proposal's
reference parser), then checks the structure and requests each linked URL.
Usage: python validate.py http://127.0.0.1:8000/docs/llms.txt
"""
import re
import sys
import urllib.request

from llms_txt import parse_llms_file


def fetch(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8")


def main(url):
    status, ctype, text = fetch(url)
    print(f"GET {url} -> HTTP {status}, {ctype}, {len(text)} bytes, {len(text.split())} words")
    problems = []
    # Under an H2, every line must be a list item with a Markdown link: - [name](url): notes
    section = None
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            section = line[3:]
        elif section and line.strip() and not re.match(r"^\s*- \[[^\]]+\]\([^)]+\)", line):
            problems.append(f"line {number} in section '{section}' is not a '- [name](url)' item: {line[:60]}")
    if problems:
        print("PROBLEMS:\n- " + "\n- ".join(problems))
        return 1
    parsed = parse_llms_file(text)
    if not text.startswith("# "):
        problems.append("the file must start with an H1 (# Name)")
    if not parsed.get("summary"):
        problems.append("no blockquote summary (> ...) after the H1")
    print(f"title:    {parsed.get('title')}")
    print(f"summary:  {parsed.get('summary')}")
    for section, links in parsed.get("sections", {}).items():
        print(f"section:  {section} ({len(links)} links)")
        if not links:
            problems.append(f"section '{section}' has no [name](url) list items")
        for link in links:
            try:
                code, ltype, body = fetch(link["url"])
                note = "" if link["url"].endswith((".md", ".txt", ".yaml")) else "  (not a Markdown URL)"
                print(f"  {code} {ltype:<28} {len(body):>5} bytes  {link['title']}{note}")
            except Exception as err:  # broken link
                problems.append(f"broken link {link['url']}: {err}")
    print("OK" if not problems else "PROBLEMS:\n- " + "\n- ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/docs/llms.txt"))
