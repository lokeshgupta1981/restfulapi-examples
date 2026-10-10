Source code for the article [Agent Skills vs MCP](https://restfulapi.net/agent-skills-vs-mcp/)

# Agent Skills vs MCP example

One refund request handled with an Agent Skill and an MCP server, without a model. The script makes the choices a model would make and prints every piece of text that would enter the model's context, with an estimated token count.

- `.agents/skills/refund-policy/` is an Agent Skill in the agentskills.io format: `SKILL.md` with YAML frontmatter, a rules file in `references/` and a calculation script in `scripts/`.
- `.agents/skills/Bad_Name/` breaks the naming rules on purpose, so the loader skips it.
- `skill_loader.py` discovers skills, builds the catalog the model sees at session start, and activates a skill on demand.
- `billing_mcp_server.py` is a stdio MCP server (protocol 2026-07-28) with the tools `get_invoice` and `issue_refund`. It also serves the refund-policy skill through the MCP Skills extension (SEP-2640): it declares the extension in `server/discover` and answers `skills/list`, `skills/get` and `resources/read` on `skill://` URIs, with SHA-256 digests of every file.

## Versions

Python 3.13, PyYAML 6.0.3.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python demo.py
```

`OUTPUTS.txt` holds the output of a real run.
