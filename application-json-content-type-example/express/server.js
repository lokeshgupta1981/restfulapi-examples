import express from 'express';

const app = express();
const port = Number(process.env.PORT || 9301);

// express.json() parses the body only when Content-Type is application/json.
// Any other type is skipped and req.body stays undefined.
app.use(express.json());

app.post('/orders', (req, res) => {
  if (!req.is('application/json')) {
    res.status(415)
      .set('Accept', 'application/json')
      .type('application/problem+json')
      .send(JSON.stringify({
        type: 'about:blank',
        title: 'Unsupported Media Type',
        status: 415,
        detail: 'Send the order as application/json.'
      }));
    return;
  }
  const order = req.body;
  res.status(201).json({ id: 1001, item: order.item, quantity: order.quantity });
});

// A route without the req.is() check, to show what happens by default.
app.post('/orders-unchecked', (req, res) => {
  res.status(201).json({ receivedBody: req.body ?? null });
});

// Errors from express.json(): invalid JSON (400) or an unsupported charset (415).
app.use((err, req, res, next) => {
  res.status(err.status || 500)
    .type('application/problem+json')
    .send(JSON.stringify({ title: err.type, status: err.status, detail: err.message }));
});

app.listen(port, '127.0.0.1', () => console.log(`Express app on http://127.0.0.1:${port}`));
