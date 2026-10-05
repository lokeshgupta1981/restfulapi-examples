import { test } from "node:test";
import assert from "node:assert/strict";
import { createApp } from "./server.js";

test("bulk cancel returns HTTP 207 with one result per item", async () => {
  const server = createApp().listen(0);
  const { port } = server.address();
  const response = await fetch("http://127.0.0.1:" + port + "/orders/bulk-cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items: [{ orderId: "ord-1001" }, { orderId: "ord-1002" }] }),
  });
  const body = await response.json();
  server.close();

  assert.equal(response.status, 207);
  assert.deepEqual(body.results.map((result) => result.status), [200, 409]);
  assert.deepEqual(body.summary, { succeeded: 1, failed: 1 });
});
