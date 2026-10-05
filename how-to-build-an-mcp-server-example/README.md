Source code for the article [How to Build an MCP Server, Step by Step](https://restfulapi.net/how-to-build-an-mcp-server/)

An MCP server for a small project task tracker backed by SQLite. It has four tools, one static resource, one resource template and one prompt, and it runs over stdio or Streamable HTTP.

## Versions

- Python 3.10 or later (tested with Python 3.13.16)
- mcp 2.3.0 (Python SDK, speaks MCP protocol 2026-07-28 and falls back to older versions)
- MCP Inspector 2.9.0 (needs Node.js 22.19 or later, tested with Node.js 22.22.0)

## Files

| File | What it does |
|---|---|
| `db.py` | Creates `tasks.db` with 2 projects and 6 tasks. Run it again to reset the data. |
| `server.py` | The MCP server: tools `search_tasks`, `create_task`, `complete_task`, `project_report`; resources `tasks://projects` and `tasks://projects/{key}/summary`; prompt `weekly_update`. |
| `client.py` | A small test client that calls every feature over stdio or HTTP. |
| `mcp.json` | A sample host configuration (`mcpServers`). Replace `/path/to/` with your absolute path. |
| `mistakes/` | Small demos of common mistakes: printing to stdout in a stdio server, a blocking call inside an async tool, and a vague tool definition. |
| `OUTPUTS.txt` | Captured output of the commands below (all except the web UI). |

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python db.py
```

Test over stdio (the client starts the server as a subprocess):

```bash
python client.py stdio
```

Test over Streamable HTTP (two terminals):

```bash
python server.py --http            # listens on http://127.0.0.1:8040/mcp
python client.py http
```

Test with the MCP Inspector CLI:

```bash
npx -y @modelcontextprotocol/inspector@2.9.0 --cli python server.py --protocol-era modern --method tools/list
npx -y @modelcontextprotocol/inspector@2.9.0 --cli python server.py --protocol-era modern --method tools/call --tool-name search_tasks --tool-arg project=WEB status=todo
npx -y @modelcontextprotocol/inspector@2.9.0 --cli http://127.0.0.1:8040/mcp --protocol-era modern --method tools/call --tool-name project_report --tool-arg project=APP today=2026-10-10
```

Open the Inspector web UI:

```bash
npx -y @modelcontextprotocol/inspector@2.9.0 python server.py
```

Run the mistake demos:

```bash
cd mistakes
python print_client.py
python blocking_server.py          # terminal 1, listens on port 8041
python blocking_client.py          # terminal 2
python vague_tool.py
```
