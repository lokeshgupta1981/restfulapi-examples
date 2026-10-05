// Sends a 17,000-character Authorization header to a plain Node.js server.
// Node.js rejects request headers larger than 16 KiB by default.
import http from 'node:http';

const server = http.createServer((req, res) => res.end('ok')).listen(9499, async () => {
  const bigToken = 'Bearer ' + 'a'.repeat(17000);
  const response = await fetch('http://127.0.0.1:9499/', { headers: { Authorization: bigToken } });
  console.log(process.version, response.status, response.statusText);
  server.close();
});
