// Starts a second Express app on port 9399 that accepts application/json and every
// +json type, sends three requests to it and stops.
import express from 'express';

const jsonTypes = ['application/json', 'application/*+json'];

const app = express();
// Parse application/json and every +json type, for example application/merge-patch+json.
app.use(express.json({ type: jsonTypes }));

app.post('/orders', (req, res) => {
  // req.is() must accept the same list, otherwise +json bodies still get HTTP 415.
  if (!req.is(jsonTypes)) {
    res.status(415).set('Accept', jsonTypes.join(', ')).end();
    return;
  }
  const order = req.body;
  res.status(201).json({ id: 1001, item: order.item, quantity: order.quantity });
});

const server = app.listen(9399, '127.0.0.1', async () => {
  for (const type of ['application/vnd.acme.order+json', 'application/merge-patch+json', 'text/plain']) {
    const response = await fetch('http://127.0.0.1:9399/orders', {
      method: 'POST',
      headers: { 'Content-Type': type },
      body: '{"item":"keyboard","quantity":2}',
    });
    const accept = response.headers.get('accept');
    const line = [type, response.status, accept ? 'Accept: ' + accept : '', await response.text()];
    console.log(line.filter(Boolean).join(' '));
  }
  server.close();
});
