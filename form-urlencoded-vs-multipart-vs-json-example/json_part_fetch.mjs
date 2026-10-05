// Sends a JSON part and a file part in one multipart request from fetch(),
// to the Express server (port 9171). Run from the example root folder.
import { readFile } from "node:fs/promises";

const ticket = { subject: "Login fails & shows 500", tags: ["auth"], customer: { id: "c-1042", plan: "pro" } };
const logBytes = await readFile("error.log");

const form = new FormData();
form.append("ticket", new Blob([JSON.stringify(ticket)], { type: "application/json" }));
form.append("attachment", new Blob([logBytes], { type: "text/plain" }), "error.log");

const response = await fetch("http://127.0.0.1:9171/tickets/with-attachment", { method: "POST", body: form });
console.log(response.status, await response.text());
