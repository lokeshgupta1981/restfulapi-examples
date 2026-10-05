// Same test with the fetch() built into Node.js (it follows the Fetch Standard).
const baseUrl = process.argv[2] ?? "http://127.0.0.1:9182";
const body = JSON.stringify({ amount: "49.90" });

console.log(`Node.js ${process.version} fetch()`);
for (const code of [302, 303, 307]) {
  for (const method of ["POST", "PUT", "DELETE"]) {
    const response = await fetch(`${baseUrl}/redirect/${code}`, {
      method,
      body,
      headers: { "Content-Type": "application/json" },
    });
    const echo = await response.json();
    console.log(`${method.padEnd(8)}${String(code).padEnd(8)}${echo.method} body=${echo.body_bytes}`);
  }
}
