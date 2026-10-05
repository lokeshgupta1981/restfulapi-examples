// A small "real" Orders API used to show what a validation proxy catches.
// By default it has two contract bugs: total is a JSON number and createdAt
// is not in openapi.yaml. Start it with FIXED=1 to send the documented shape.
import http from 'node:http';

const PORT = Number(process.env.PORT ?? 9223);
const FIXED = process.env.FIXED === '1';

const order = FIXED
  ? { id: 'ord_1001', status: 'pending', currency: 'USD', total: '59.90',
      items: [{ sku: 'BOOK-REST-101', quantity: 2 }] }
  : { id: 'ord_1001', status: 'pending', currency: 'USD', total: 59.9,
      items: [{ sku: 'BOOK-REST-101', quantity: 2 }], createdAt: '2026-10-05T09:30:00Z' };
const orders = new Map([[order.id, order]]);

function send(res, status, body, headers = {}) {
  res.writeHead(status, { 'Content-Type': 'application/json', ...headers });
  res.end(JSON.stringify(body));
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://' + req.headers.host);
  const match = url.pathname.match(/^\/orders\/([^/]+)$/);
  if (req.method === 'GET' && match) {
    const found = orders.get(match[1]);
    if (!found) {
      send(res, 404, { type: 'https://api.example.com/problems/order-not-found', title: 'Order not found', status: 404 },
        { 'Content-Type': 'application/problem+json' });
      return;
    }
    send(res, 200, found);
    return;
  }
  if (req.method === 'GET' && url.pathname === '/orders') {
    send(res, 200, { items: [...orders.values()] });
    return;
  }
  send(res, 404, { type: 'about:blank', title: 'Not Found', status: 404 },
    { 'Content-Type': 'application/problem+json' });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('Real API listening on http://127.0.0.1:' + PORT);
});
