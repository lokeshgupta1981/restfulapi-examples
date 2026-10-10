"""A small billing MCP server over stdio (protocol 2026-07-28).

Tools: get_invoice, issue_refund. It also serves the refund-policy skill with the
Skills extension (SEP-2640): it declares io.modelcontextprotocol/skills in server/discover
and answers skills/list, skills/get and resources/read on skill:// URIs.
"""

import hashlib
import json
import pathlib
import sys

import yaml

SKILL_DIR = pathlib.Path(__file__).with_name(".agents") / "skills" / "refund-policy"
INVOICES = {"INV-2041": {"customer": "Ana Costa", "plan": "annual", "amount_cents": 120000, "days_since_invoice": 45}}
TOOLS = [
    {"name": "get_invoice", "description": "Return one invoice with plan, amount and age in days.",
     "inputSchema": {"type": "object", "properties": {"invoice_id": {"type": "string"}}, "required": ["invoice_id"]}},
    {"name": "issue_refund", "description": "Refund an amount in cents on an invoice.",
     "inputSchema": {"type": "object", "properties": {"invoice_id": {"type": "string"},
                                                      "amount_cents": {"type": "integer"}},
                     "required": ["invoice_id", "amount_cents"]},
     "annotations": {"destructiveHint": True}},
]


def skill_files() -> dict[str, pathlib.Path]:
    return {f"skill://refund-policy/{p.relative_to(SKILL_DIR).as_posix()}": p
            for p in sorted(SKILL_DIR.rglob("*")) if p.is_file()}


def skill_entry() -> dict:
    """The SEP-2640 entry: verbatim frontmatter plus every file with its SHA-256 digest and size."""
    frontmatter = yaml.safe_load((SKILL_DIR / "SKILL.md").read_text().split("---", 2)[1])
    resources = [{"uri": uri, "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                  "size": path.stat().st_size} for uri, path in skill_files().items()]
    return {"uri": "skill://refund-policy/SKILL.md", "frontmatter": frontmatter, "resources": resources}


def handle(message: dict) -> dict:
    method, params = message["method"], message.get("params", {})
    if method == "server/discover":
        result = {"supportedVersions": ["2026-07-28"],
                  "capabilities": {"tools": {}, "resources": {},
                                   "extensions": {"io.modelcontextprotocol/skills": {}}},
                  "ttlMs": 3600000, "cacheScope": "public"}
    elif method == "tools/list":
        result = {"tools": TOOLS, "ttlMs": 300000, "cacheScope": "public"}
    elif method == "tools/call" and params["name"] == "get_invoice":
        invoice = INVOICES[params["arguments"]["invoice_id"]]
        result = {"content": [{"type": "text", "text": json.dumps(invoice)}], "isError": False}
    elif method == "tools/call" and params["name"] == "issue_refund":
        args = params["arguments"]
        result = {"content": [{"type": "text", "text": f"refunded {args['amount_cents']} cents on {args['invoice_id']}"}],
                  "isError": False}
    elif method == "skills/list":
        result = {"skills": [skill_entry()], "ttlMs": 300000, "cacheScope": "public"}
    elif method == "skills/get" and params["uri"] == "skill://refund-policy/SKILL.md":
        result = {"skill": skill_entry()}
    elif method == "resources/read":
        text = skill_files()[params["uri"]].read_text()
        result = {"contents": [{"uri": params["uri"], "mimeType": "text/markdown", "text": text}]}
    else:
        return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": message["id"], "result": {"resultType": "complete", **result}}


for line in sys.stdin:
    if line.strip():
        sys.stdout.write(json.dumps(handle(json.loads(line))) + "\n")
        sys.stdout.flush()
