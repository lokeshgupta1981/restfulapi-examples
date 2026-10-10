"""Builds an llms.txt, an llms-full.txt and one Markdown page per API tag from openapi.yaml.

Output goes to site/docs/. The links in llms.txt point to the .md pages, as the
llms.txt proposal recommends. Usage: python generate.py [base_url]
"""
import json
import shutil
import sys
from pathlib import Path

import yaml

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
HERE = Path(__file__).parent
OUT = HERE / "site" / "docs"
GUIDES = [("authentication", "How to send the API key"), ("errors", "Error format and which errors to retry")]


def slug(text):
    return text.lower().replace(" ", "-")


def operation_md(method, path, op):
    lines = [f"## {op['summary']}", "", f"`{method.upper()} {path}`", "", op.get("description", ""), ""]
    params = op.get("parameters", [])
    if params:
        lines += ["| Parameter | In | Required | Type |", "|---|---|---|---|"]
        for p in params:
            schema = p.get("schema", {})
            kind = schema.get("type", "")
            if "enum" in schema:
                kind += " (" + ", ".join(schema["enum"]) + ")"
            lines.append(f"| {p['name']} | {p['in']} | {'yes' if p.get('required') else 'no'} | {kind} |")
        lines.append("")
    body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("example")
    if body:
        lines += ["Request body:", "", "```json", json.dumps(body), "```", ""]
    for code, resp in op.get("responses", {}).items():
        lines.append(f"- HTTP {code}: {resp['description']}")
        example = resp.get("content", {}).get("application/json", {}).get("example")
        if example:
            lines += ["", "  ```json", "  " + json.dumps(example), "  ```"]
    return "\n".join(lines) + "\n"


def main():
    spec = yaml.safe_load((HERE / "openapi.yaml").read_text())
    shutil.rmtree(HERE / "site", ignore_errors=True)
    OUT.mkdir(parents=True)
    info, server = spec["info"], spec["servers"][0]["url"]

    # One Markdown page per tag, with every operation of that tag.
    pages = {}
    for tag in spec["tags"]:
        parts = [f"# {tag['name']}", "", tag["description"], "", f"Base URL: {server}", ""]
        for path, item in spec["paths"].items():
            for method, op in item.items():
                if tag["name"] in op.get("tags", []):
                    parts.append(operation_md(method, path, op))
        pages[slug(tag["name"])] = "\n".join(parts)
        (OUT / f"{slug(tag['name'])}.md").write_text(pages[slug(tag["name"])])

    for name, _ in GUIDES + [("changelog", "")]:
        pages[name] = (HERE / "guides" / f"{name}.md").read_text()
        (OUT / f"{name}.md").write_text(pages[name])
    shutil.copy(HERE / "openapi.yaml", OUT / "openapi.yaml")

    llms = [
        f"# {info['title']}",
        "",
        f"> {info['description']} Base URL {server}, API version {info['version']}.",
        "",
        "Important notes for agents:",
        "",
        "- Every request needs an Authorization: Bearer header with an API key.",
        "- POST /orders requires an Idempotency-Key header. Reuse the same key when you retry.",
        "- Amounts are integers in the smallest currency unit (4990 means 49.90 EUR).",
        "",
        "## Guides",
        "",
    ]
    llms += [f"- [{name.capitalize()}]({BASE}/docs/{name}.md): {note}" for name, note in GUIDES]
    llms += ["", "## API reference", ""]
    llms += [f"- [{t['name']}]({BASE}/docs/{slug(t['name'])}.md): {t['description']}" for t in spec["tags"]]
    llms += [
        "",
        "## Optional",
        "",
        f"- [Changelog]({BASE}/docs/changelog.md): Changes by date",
        f"- [OpenAPI document]({BASE}/docs/openapi.yaml): The full machine-readable API description",
        "",
    ]
    (OUT / "llms.txt").write_text("\n".join(llms))

    # llms-full.txt: a common convention (not part of the proposal) with all pages in one file.
    full = [f"# {info['title']}\n\n> {info['description']}\n"]
    full += [pages[name] for name in ["authentication", "errors"] + [slug(t["name"]) for t in spec["tags"]]]
    (OUT / "llms-full.txt").write_text("\n\n".join(p.strip() + "\n" for p in full))

    for f in sorted(OUT.iterdir()):
        print(f"{f.relative_to(HERE)}  {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
