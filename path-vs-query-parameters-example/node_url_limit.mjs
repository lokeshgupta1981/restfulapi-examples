// Sends long URLs to a plain Node.js HTTP server (default maxHeaderSize).
import http from "node:http";

console.log("http.maxHeaderSize:", http.maxHeaderSize);
const server = http.createServer((req, res) => res.end("ok"));
server.listen(8482, async () => {
  for (const size of [16000, 16300]) {
    const response = await fetch("http://localhost:8482/orders?note=" + "x".repeat(size));
    console.log("query value of " + size + " characters: HTTP " + response.status);
  }
  server.close();
});
