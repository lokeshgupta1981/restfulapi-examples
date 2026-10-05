// Sends the same ticket three ways with fetch() in Node.js 22.
// Start wire_server.py first. Run from the example root folder.
import { readFile } from "node:fs/promises";

const url = "http://127.0.0.1:9170/tickets";

const form = new URLSearchParams();
form.append("subject", "Login fails & shows 500");
form.append("priority", "high");
form.append("tags", "auth");
form.append("tags", "web");
await fetch(url, { method: "POST", body: form });

const multipart = new FormData();
multipart.append("subject", "Login fails & shows 500");
multipart.append("priority", "high");
const logBytes = await readFile("error.log");
multipart.append("attachment", new Blob([logBytes], { type: "text/plain" }), "error.log");
await fetch(url, { method: "POST", body: multipart });

const ticket = { subject: "Login fails & shows 500", priority: "high", tags: ["auth", "web"] };
await fetch(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(ticket),
});

// Mistake: a JSON string without a Content-Type header
await fetch(url, { method: "POST", body: JSON.stringify(ticket) });

console.log("sent 4 requests");
