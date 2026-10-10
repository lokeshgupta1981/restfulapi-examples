"""Walk through one refund request with a skill and an MCP server, step by step.

No model runs here: the script makes the choices a model would make, so that
every piece of text that would enter the model's context is printed and measured.
Token counts are estimates (characters / 4).
"""

import hashlib
import json
import pathlib
import subprocess
import sys

from skill_loader import activate, catalog, discover

HERE = pathlib.Path(__file__).parent
ROOT = HERE / ".agents" / "skills"


def tokens(text: str) -> int:
    return len(text) // 4


class McpClient:
    """Talks to billing_mcp_server.py over stdio, one JSON-RPC message per line."""

    def __init__(self):
        self.process = subprocess.Popen([sys.executable, str(HERE / "billing_mcp_server.py")],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.next_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": {**(params or {}), "_meta": meta}}
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())["result"]

    def close(self):
        self.process.stdin.close()
        self.process.wait()


print("== 1. Discover skills (tier 1 metadata only)")
skills = discover(ROOT)
print(f"loaded: {', '.join(skills)}")

print("\n== 2. What the model sees at session start")
skill_catalog = catalog(skills)
print(skill_catalog)
mcp = McpClient()
tools = mcp.call("tools/list")["tools"]
tool_text = json.dumps(tools)
print(f"skill catalog: {len(skill_catalog)} chars, about {tokens(skill_catalog)} tokens")
print(f"MCP tool definitions: {len(tools)} tools, {len(tool_text)} chars, about {tokens(tool_text)} tokens")

print("\n== 3. User: 'Ana Costa wants a refund for invoice INV-2041.' The model activates refund-policy (tier 2)")
content = activate(skills, "refund-policy")
print(content)
print(f"activated skill: about {tokens(content)} tokens, loaded only now")

print("\n== 4. Step 1 of the skill: the MCP tool fetches live data")
invoice = json.loads(mcp.call("tools/call", {"name": "get_invoice", "arguments": {"invoice_id": "INV-2041"}})["content"][0]["text"])
print(f"get_invoice -> {invoice}")

print("\n== 5. Steps 2 and 3: read the rules file (tier 3) and run the bundled script")
rules = (ROOT / "refund-policy" / "references" / "REFUND-RULES.md").read_text()
print(f"read references/REFUND-RULES.md: about {tokens(rules)} tokens")
script = ROOT / "refund-policy" / "scripts" / "calculate_refund.py"
args = [invoice["plan"], str(invoice["days_since_invoice"]), str(invoice["amount_cents"])]
output = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True).stdout.strip()
print(f"$ python scripts/calculate_refund.py {' '.join(args)}")
print(output)

print("\n== 6. Step 4: the rule in the skill decides what happens next")
refund = int(output.split()[0].split("=")[1])
if refund > 50000:
    print(f"refund {refund} cents is above 50000, so the agent asks a human approver and does not call issue_refund yet")
else:
    print(mcp.call("tools/call", {"name": "issue_refund",
                                  "arguments": {"invoice_id": "INV-2041", "amount_cents": refund}})["content"][0]["text"])

print("\n== 7. The same skill served by the MCP server (Skills extension, SEP-2640)")
extensions = mcp.call("server/discover")["capabilities"]["extensions"]
print(f"server/discover -> extensions: {list(extensions)}")
entry = mcp.call("skills/list")["skills"][0]
print(f"skills/list -> {entry['uri']}, name {entry['frontmatter']['name']}, {len(entry['resources'])} files")
for resource in entry["resources"]:
    print(f"   {resource['uri']}  {resource['digest'][:19]}...  {resource['size']} bytes")
text = mcp.call("resources/read", {"uri": entry["uri"]})["contents"][0]["text"]
digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
print(f"resources/read {entry['uri']} -> digest matches the listing: {digest == entry['resources'][0]['digest']}")
mcp.close()
