// Starts the order-desk server the way a host does and prints what goes wrong.
// Usage: node check.mjs <scenario>
//   good | missing-command | stdout-text | missing-key | missing-key-fixed | slow
//   http-good | http-wrong-path | http-not-running
// TIMEOUT_MS sets the per-request timeout (default 60000, the SDK default).
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const python = process.env.PYTHON || "python3";
const server = path.join(here, "..", "servers", "order_server.py");

const scenarios = {
  "good": { command: python, args: [server] },
  "missing-command": { command: "order-desk-server", args: [] },
  "stdout-text": { command: python, args: [server], env: { ORDER_DESK_FAULT: "stdout" } },
  "missing-key": { command: python, args: [server], env: { ORDER_DESK_FAULT: "missing-key" } },
  "missing-key-fixed": {
    command: python,
    args: [server],
    env: { ORDER_DESK_FAULT: "missing-key", ORDER_API_KEY: "test-key-123" },
  },
  "slow": { command: python, args: [server], env: { ORDER_DESK_FAULT: "slow" } },
  // Streamable HTTP scenarios. Start servers/http_server.py first.
  "http-good": { url: "http://127.0.0.1:8000/mcp" },
  "http-wrong-path": { url: "http://127.0.0.1:8000/sse" },
  "http-not-running": { url: "http://127.0.0.1:8009/mcp" },
};

const name = process.argv[2] || "good";
const params = scenarios[name];
const transport = params.url
  ? new StreamableHTTPClientTransport(new URL(params.url))
  : new StdioClientTransport({ ...params, stderr: "pipe" });
transport.stderr?.on("data", (chunk) => process.stdout.write("[server stderr] " + chunk));
transport.onerror = (err) => console.log("[transport error] " + err.message);

const client = new Client({ name: "connection-check", version: "1.0.0" });
const timeout = Number(process.env.TIMEOUT_MS || 60000);

try {
  await client.connect(transport, { timeout });
  const tools = await client.listTools(undefined, { timeout });
  console.log("tools: " + tools.tools.map((t) => t.name).join(", "));
  const result = await client.callTool(
    { name: "get_order_status", arguments: { order_id: "A-1001" } },
    { timeout },
  );
  console.log("result: " + result.content[0].text);
} catch (err) {
  console.log("[" + name + "] " + err.constructor.name + ": " + err.message);
} finally {
  await client.close().catch(() => {});
}
