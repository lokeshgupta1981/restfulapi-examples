// Consumer tests for OrdersClient. BASE_URL selects the mock (or real API) to run against.
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { OrdersClient } from './orders-client.js';

const baseUrl = process.env.BASE_URL ?? 'http://127.0.0.1:9222';
const client = new OrdersClient(baseUrl);

beforeEach(async () => {
  // The stateful mock offers a reset endpoint; other servers answer 404, which we ignore.
  await fetch(baseUrl + '/__reset', { method: 'POST' });
});

test('a created order can be read back', async () => {
  const created = await client.createOrder({ currency: 'EUR', items: [{ sku: 'PEN-BLUE-7', quantity: 3 }] });
  assert.equal(created.status, 201);
  const fetched = await client.getOrder(created.body.id);
  assert.equal(fetched.status, 200);
  assert.equal(fetched.body.currency, 'EUR');
});

test('an invalid order gets HTTP 422', async () => {
  const created = await client.createOrder({ currency: 'EUR', items: [{ sku: 'PEN-BLUE-7', quantity: 0 }] });
  assert.equal(created.status, 422);
});
