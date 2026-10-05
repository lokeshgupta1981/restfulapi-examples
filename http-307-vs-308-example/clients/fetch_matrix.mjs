// Send POST and PUT to /lab/<code> with fetch() and print what reached /echo.
const BASE = "http://127.0.0.1:9190";
const ORDER = '{"sku": "BOOK-42", "qty": 2}';
const HEADERS = { "Content-Type": "application/json", Authorization: "Bearer demo-token" };

for (const method of ["POST", "PUT"]) {
  for (const code of [301, 302, 303, 307, 308]) {
    const response = await fetch(BASE + "/lab/" + code, { method, headers: HEADERS, body: ORDER });
    const seen = await response.json();
    console.log(method.padEnd(4) + " " + code + " -> " + seen.summary);
  }
}

const cross = await fetch(BASE + "/lab/308?cross=1", { method: "POST", headers: HEADERS, body: ORDER });
console.log("POST 308 to another host -> " + (await cross.json()).summary);

// A stream body cannot be sent a second time, so fetch() cannot follow 307 or 308.
try {
  const stream = new Blob([ORDER]).stream();
  await fetch(BASE + "/lab/307", { method: "POST", headers: HEADERS, body: stream, duplex: "half" });
} catch (error) {
  const where = error.cause.stack.split("\n")[2].trim();
  console.log("POST 307 with a stream body -> " + error.name + ": " + error.message + " (" + where.split(" ")[1] + ")");
}
