// fetch() refuses to send a body with GET.
try {
  await fetch("http://localhost:9120/orders", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: ["paid"] }),
  });
} catch (error) {
  console.log(error.name + ": " + error.message);
}

// The same filter as a POST search works.
const response = await fetch("http://localhost:9120/orders/search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ status: ["paid"] }),
});
console.log(response.status, await response.text());
