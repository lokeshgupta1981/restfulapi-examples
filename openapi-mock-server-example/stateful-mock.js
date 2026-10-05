// Stateful mock of the Orders API: validates requests against openapi.yaml
// and keeps created orders in memory until the process stops or /__reset is called.
import http from 'node:http';
import { OpenAPIBackend } from 'openapi-backend';

const PORT = Number(process.env.PORT ?? 9222);
const UNIT_PRICE_CENTS = 1250; // fixed mock price per unit: 12.50

let orders = new Map();
// New IDs start after the example IDs ord_1000 to ord_1002 in openapi.yaml.
let nextId = 1003;

const PROBLEMS = 'https://api.example.com/problems/';

function problem(status, type, title, detail, extra = {}) {
  return {
    status,
    headers: { 'Content-Type': 'application/problem+json' },
    body: { type, title, status, detail, ...extra },
  };
}

const api = new OpenAPIBackend({ definition: './openapi.yaml', ajvOpts: { allErrors: true } });

api.register({
  createOrder: (c) => {
    const newOrder = c.request.requestBody;
    const units = newOrder.items.reduce((sum, item) => sum + item.quantity, 0);
    const order = {
      id: 'ord_' + nextId++,
      status: 'pending',
      currency: newOrder.currency,
      total: (units * UNIT_PRICE_CENTS / 100).toFixed(2),
      items: newOrder.items,
    };
    orders.set(order.id, order);
    return { status: 201, headers: { Location: '/orders/' + order.id }, body: order };
  },
  getOrder: (c) => {
    const order = orders.get(c.request.params.orderId);
    if (!order) {
      return problem(404, PROBLEMS + 'order-not-found', 'Order not found', 'No order exists with ID ' + c.request.params.orderId + '.');
    }
    return { status: 200, body: order };
  },
  listOrders: (c) => {
    const status = c.request.query.status;
    const items = [...orders.values()].filter((o) => !status || o.status === status);
    return { status: 200, body: { items } };
  },
  validationFail: (c) => {
    const errors = c.validation.errors.map((e) => ({ pointer: e.instancePath || '/', message: e.message }));
    return problem(422, PROBLEMS + 'validation', 'Validation failed', 'The request does not match openapi.yaml.', { errors });
  },
  notFound: () => problem(404, 'about:blank', 'Not Found', 'No operation in openapi.yaml matches this path.'),
  methodNotAllowed: (c) => {
    const allow = ['get', 'post', 'put', 'patch', 'delete']
      .filter((method) => c.api.router.matchOperation({ ...c.request, method }))
      .map((method) => method.toUpperCase());
    const result = problem(405, 'about:blank', 'Method Not Allowed', 'The path exists but not with this method.');
    result.headers.Allow = allow.join(', ');
    return result;
  },
  // Any operation without a handler above answers with data built from its schema.
  notImplemented: (c) => {
    const { status, mock } = c.api.mockResponseForOperation(c.operation.operationId);
    return { status, body: mock };
  },
});

await api.init();

function readBody(req) {
  return new Promise((resolve) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; });
    req.on('end', () => resolve(data));
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://' + req.headers.host);
  if (req.method === 'POST' && url.pathname === '/__reset') {
    orders = new Map();
    nextId = 1003;
    res.writeHead(204).end();
    return;
  }
  const raw = await readBody(req);
  let body;
  try {
    body = raw ? JSON.parse(raw) : undefined;
  } catch {
    const result = problem(400, 'about:blank', 'Bad Request', 'The body is not valid JSON.');
    res.writeHead(result.status, result.headers).end(JSON.stringify(result.body));
    return;
  }
  const result = await api.handleRequest({
    method: req.method,
    path: url.pathname,
    query: Object.fromEntries(url.searchParams),
    headers: req.headers,
    body,
  });
  const headers = { 'Content-Type': 'application/json', ...result.headers };
  res.writeHead(result.status, headers).end(JSON.stringify(result.body));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('Stateful mock listening on http://127.0.0.1:' + PORT);
});
