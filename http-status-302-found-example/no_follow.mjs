// Reads the HTTP 302 instead of following it (Node.js; browsers return an opaque response instead).
const paymentResponse = await fetch("http://127.0.0.1:9182/redirect/302", {
  method: "POST",
  body: JSON.stringify({ amount: "49.90" }),
  headers: { "Content-Type": "application/json" },
  redirect: "manual",
});
console.log("fetch():", paymentResponse.status, paymentResponse.headers.get("Location"));
