// Two common fetch() mistakes, sent to the Express server (port 9171).
const url = "http://127.0.0.1:9171/tickets";
const ticket = { subject: "Login fails & shows 500", priority: "high" };

// Mistake 1: JSON.stringify() without a Content-Type header
let response = await fetch(url, { method: "POST", body: JSON.stringify(ticket) });
console.log("JSON string, no header:", response.status, await response.text());

// Mistake 2: a hand-written multipart Content-Type replaces the one with the boundary
const form = new FormData();
form.append("subject", "Login fails & shows 500");
response = await fetch(url, {
  method: "POST",
  headers: { "Content-Type": "multipart/form-data" },
  body: form,
});
console.log("FormData, manual header:", response.status, await response.text());

// Fixed: let fetch() set the header for FormData, set it ourselves for JSON
response = await fetch(url, { method: "POST", body: form });
console.log("FormData, no header:", response.status, await response.text());
response = await fetch(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(ticket),
});
console.log("JSON with header:", response.status, await response.text());
