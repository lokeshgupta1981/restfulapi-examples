// Streams orders as JSON Lines, one line every 200 ms, so clients can process them as they arrive.
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';

const PORT = Number(process.env.PORT ?? 9387);
const orders = readFileSync('data/orders.jsonl', 'utf8')
  .split('\n')
  .filter((line) => line.trim() !== '')
  .map((line) => JSON.parse(line));

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const server = createServer(async (req, res) => {
  if (req.url === '/orders') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(orders));
    return;
  }
  if (req.url === '/orders/export') {
    res.writeHead(200, { 'Content-Type': 'application/jsonl' });
    for (const order of orders) {
      res.write(JSON.stringify(order) + '\n');
      await wait(200);
    }
    res.end();
    return;
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found' }));
});

server.listen(PORT, '127.0.0.1', () => console.log('listening on http://127.0.0.1:' + PORT));
