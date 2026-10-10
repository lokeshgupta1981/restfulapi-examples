"""An MCP server with an MCP App (extension io.modelcontextprotocol/ui) for a warehouse inventory.

Protocol 2026-07-28 over Streamable HTTP (POST /mcp, JSON responses). The server offers
  - show_inventory   tool for the model and the app, linked to the UI resource ui://inventory/dashboard
  - restock_item     tool for the app only (visibility ["app"]), so the model never sees it
  - export_report    tool for the model only (visibility ["model"]), so the app may not call it
  - ui://inventory/dashboard   the HTML view (mimeType text/html;profile=mcp-app)

GET /host serves host.html, a minimal test host that renders the view in a sandboxed iframe.
It is a local test page, not a production host.

Run: uvicorn server:app --host 127.0.0.1 --port 8000   then open http://127.0.0.1:8000/host
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

PROTOCOL_VERSION = "2026-07-28"
UI_EXT = "io.modelcontextprotocol/ui"
APP_MIME = "text/html;profile=mcp-app"
VIEW_URI = "ui://inventory/dashboard"
HERE = Path(__file__).parent

app = FastAPI()
STOCK = {  # warehouse -> sku -> item
    "berlin": {"KB-01": {"sku": "KB-01", "name": "Keyboard", "stock": 42, "reorderAt": 20},
               "MS-02": {"sku": "MS-02", "name": "Mouse", "stock": 8, "reorderAt": 25},
               "HD-07": {"sku": "HD-07", "name": "Headset", "stock": 3, "reorderAt": 10}},
}

TOOLS = [
    {"name": "show_inventory", "title": "Show inventory",
     "description": "Show the stock of one warehouse, with items below their reorder level marked.",
     "inputSchema": {"type": "object", "properties": {"warehouse": {"type": "string", "enum": ["berlin"]}},
                     "required": ["warehouse"], "additionalProperties": False},
     "_meta": {"ui": {"resourceUri": VIEW_URI, "visibility": ["model", "app"]}}},
    {"name": "restock_item", "title": "Restock item",
     "description": "Add units to one item. Used by the inventory view's Restock button.",
     "inputSchema": {"type": "object", "properties": {
         "warehouse": {"type": "string"}, "sku": {"type": "string"},
         "quantity": {"type": "integer", "minimum": 1, "maximum": 500}},
         "required": ["warehouse", "sku", "quantity"], "additionalProperties": False},
     "_meta": {"ui": {"resourceUri": VIEW_URI, "visibility": ["app"]}}},
    {"name": "export_report", "title": "Export report",
     "description": "Export the inventory of a warehouse as CSV text.",
     "inputSchema": {"type": "object", "properties": {"warehouse": {"type": "string"}},
                     "required": ["warehouse"], "additionalProperties": False},
     "_meta": {"ui": {"visibility": ["model"]}}},
]


def result(request_id, payload: dict) -> dict:
    payload.setdefault("resultType", "complete")
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def inventory_result(warehouse: str) -> dict:
    items = list(STOCK[warehouse].values())
    low = [i["sku"] for i in items if i["stock"] < i["reorderAt"]]
    text = f"{warehouse.title()} has {len(items)} items. Below reorder level: {', '.join(low) or 'none'}."
    # content is the text fallback for the model and for hosts without MCP Apps support,
    # structuredContent is the data the view renders
    return {"content": [{"type": "text", "text": text}],
            "structuredContent": {"warehouse": warehouse, "items": items}, "isError": False}


def call_tool(request_id, params: dict) -> dict:
    name, args = params.get("name"), params.get("arguments", {})
    warehouse = args.get("warehouse", "")
    if name not in {t["name"] for t in TOOLS}:
        return error(request_id, -32602, f"Unknown tool: {name}")
    if warehouse not in STOCK:
        return result(request_id, {"content": [{"type": "text", "text": f"Unknown warehouse {warehouse!r}."}],
                                   "isError": True})
    if name == "show_inventory":
        return result(request_id, inventory_result(warehouse))
    if name == "restock_item":
        item = STOCK[warehouse].get(args.get("sku"))
        if item is None:
            return result(request_id, {"content": [{"type": "text", "text": "Unknown SKU."}], "isError": True})
        item["stock"] += int(args.get("quantity", 0))
        return result(request_id, {"content": [{"type": "text", "text": f"{item['sku']} stock is {item['stock']}."}],
                                   "structuredContent": item, "isError": False})
    rows = "\n".join(f"{i['sku']},{i['stock']}" for i in STOCK[warehouse].values())
    return result(request_id, {"content": [{"type": "text", "text": "sku,stock\n" + rows}], "isError": False})


def handle(message: dict) -> dict:
    request_id, method = message.get("id"), message.get("method")
    params = message.get("params", {})
    meta = params.get("_meta", {})
    if meta.get("io.modelcontextprotocol/protocolVersion") != PROTOCOL_VERSION:
        return error(request_id, -32602, "Missing or unsupported protocol version in _meta")
    if method == "server/discover":
        return result(request_id, {"supportedVersions": [PROTOCOL_VERSION],
                                   "capabilities": {"tools": {}, "resources": {}, "extensions": {UI_EXT: {}}},
                                   "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "inventory", "version": "1.0.0"}}})
    if method == "tools/list":
        return result(request_id, {"tools": TOOLS, "ttlMs": 300000, "cacheScope": "public"})
    if method == "tools/call":
        return call_tool(request_id, params)
    if method == "resources/list":
        return result(request_id, {"resources": [{"uri": VIEW_URI, "name": "inventory-dashboard",
                                                  "mimeType": APP_MIME}], "ttlMs": 300000, "cacheScope": "public"})
    if method == "resources/read":
        if params.get("uri") != VIEW_URI:
            return error(request_id, -32602, "Resource not found")
        html = (HERE / "view.html").read_text(encoding="utf-8")
        return result(request_id, {"contents": [{
            "uri": VIEW_URI, "mimeType": APP_MIME, "text": html,
            "_meta": {"ui": {"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": True}}}],
            "ttlMs": 3600000, "cacheScope": "public"})
    return error(request_id, -32601, "Method not found")


@app.post("/mcp")
async def mcp(request: Request):
    return JSONResponse(handle(await request.json()))


@app.get("/host")
def host_page():
    return HTMLResponse((HERE / "host.html").read_text(encoding="utf-8"))
