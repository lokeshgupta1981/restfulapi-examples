Source code for the article [MCP Apps, Interactive UI in MCP](https://restfulapi.net/mcp-apps/)

# MCP Apps example

An inventory MCP server with one MCP App (extension `io.modelcontextprotocol/ui`), a view written without an SDK, and a minimal test host that renders the view in a real browser.

- `server.py` (FastAPI, MCP protocol 2026-07-28 over Streamable HTTP) offers `show_inventory` (linked to the view `ui://inventory/dashboard`), the app-only tool `restock_item` (visibility `["app"]`), and the model-only tool `export_report` (visibility `["model"]`). It serves the view as a resource with the media type `text/html;profile=mcp-app`, and the test host at `/host`.
- `view.html` is the view. It sends `ui/initialize`, renders the data from `ui/notifications/tool-result`, calls `restock_item` with `tools/call` and sends `ui/update-model-context`.
- `host.html` is a minimal test host for local development. It calls the tool, reads the resource, renders the view in an iframe with `sandbox="allow-scripts"` and the default CSP of the specification, and enforces the visibility rules. A real web host also uses a sandbox proxy on a separate origin.
- `browser_check.py` opens the test host in headless Chromium with Playwright, clicks Restock and Export, prints the host log and saves `screenshot.png`.

## Versions

Python 3.10 or later (tested with Python 3.13), FastAPI 0.143.0, Uvicorn 0.54.0, Playwright 1.56.0 with Chromium. `run_demo.sh` also needs curl.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Git Bash on Windows: source .venv/Scripts/activate
pip install -r requirements.txt
playwright install chromium
./run_demo.sh
```

To click through the view yourself, run `uvicorn server:app --port 8000` and open http://127.0.0.1:8000/host.

`OUTPUTS.txt` holds the output of a real run.
