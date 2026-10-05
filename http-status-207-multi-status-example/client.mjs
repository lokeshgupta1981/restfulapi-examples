const response = await fetch("http://127.0.0.1:9207/orders/bulk-cancel", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    items: [{ orderId: "ord-1003" }, { orderId: "ord-1002" }, { orderId: "ord-9999" }],
  }),
});
console.log("status:", response.status, "ok:", response.ok);

if (response.status === 207) {
  const body = await response.json();
  const failedItems = body.results.filter((result) => result.status >= 300);
  for (const result of failedItems) {
    console.log("failed: " + result.orderId + " -> " + result.status + " " + result.error?.detail);
  }
  console.log("cancelled " + body.summary.succeeded + " of " + body.results.length + " orders");
} else if (!response.ok) {
  const problem = await response.json();
  console.log("whole request failed:", problem.detail);
}
