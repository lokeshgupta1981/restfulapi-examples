// Signs requests for the Orders API and runs the scenarios from the article.
// Run: node client.mjs  (server on http://localhost:9410)
import { createHash, createHmac, randomBytes } from 'node:crypto';

const BASE = 'http://localhost:9410';
const KEY_ID = 'client-1-2026-10';
const SECRET = 'demo-secret-key-2026-10'; // example value, not a real key

function rfc3986(text) {
  return encodeURIComponent(text).replace(/[!'()*]/g,
    (c) => '%' + c.charCodeAt(0).toString(16).toUpperCase());
}

export function canonicalQuery(rawQuery) {
  const pairs = [...new URLSearchParams(rawQuery)];
  pairs.sort((a, b) => (a[0] === b[0] ? (a[1] < b[1] ? -1 : 1) : (a[0] < b[0] ? -1 : 1)));
  return pairs.map(([name, value]) => rfc3986(name) + '=' + rfc3986(value)).join('&');
}

export function canonicalRequest(method, host, path, rawQuery, timestamp, nonce, body) {
  const bodyHash = createHash('sha256').update(body).digest('hex');
  return [method.toUpperCase(), host.toLowerCase(), path, canonicalQuery(rawQuery),
    timestamp, nonce, bodyHash].join('\n');
}

export function sign(secret, canonical) {
  return createHmac('sha256', secret).update(canonical, 'utf8').digest('hex');
}

function authHeader(keyId, ts, nonce, sig) {
  return 'HMAC-SHA256 keyId="' + keyId + '", ts="' + ts + '", nonce="' + nonce + '", sig="' + sig + '"';
}

async function send(label, opts) {
  const method = opts.method || 'POST';
  const url = new URL(BASE + opts.path);
  const body = opts.body === undefined ? '' : opts.body;
  const ts = String(opts.ts || Math.floor(Date.now() / 1000));
  const nonce = opts.nonce || randomBytes(12).toString('hex');
  const signedBody = opts.signedBody === undefined ? body : opts.signedBody;
  const canonical = canonicalRequest(method, url.host, url.pathname, url.search.slice(1),
    ts, nonce, signedBody);
  const sig = sign(opts.secret || SECRET, canonical);
  const headers = { Authorization: authHeader(opts.keyId || KEY_ID, ts, nonce, sig) };
  if (method === 'POST') headers['Content-Type'] = 'application/json';
  const res = await fetch(url, { method, headers, body: method === 'POST' ? body : undefined });
  console.log('--- ' + label);
  console.log(res.status + ' ' + (await res.text()));
  return { canonical, sig, nonce, ts, headers };
}

const order = JSON.stringify({ item: 'keyboard', quantity: 2 });

if (process.argv[2] === 'show') {
  const canonical = canonicalRequest('POST', 'localhost:9410', '/orders',
    'note=gift+wrap&currency=USD', '1791200000', 'n-0001', '{"item":"keyboard","quantity":2}');
  console.log(canonical);
  console.log('signature: ' + sign(SECRET, canonical));
  process.exit(0);
}

const first = await send('1. valid signed POST', { path: '/orders?note=gift+wrap&currency=USD', body: order });
console.log('Authorization: ' + first.headers.Authorization);

await send('2. replay of request 1 (same nonce and timestamp)', {
  path: '/orders?note=gift+wrap&currency=USD', body: order, nonce: first.nonce, ts: first.ts });

await send('3. body changed after signing', {
  path: '/orders', body: JSON.stringify({ item: 'keyboard', quantity: 20 }), signedBody: order });

await send('4. timestamp 10 minutes old', {
  path: '/orders', body: order, ts: Math.floor(Date.now() / 1000) - 600 });

await send('5. same query, %20 instead of + and other order', {
  path: '/orders?currency=USD&note=gift%20wrap', body: order });

await send('6. GET with an empty body', { method: 'GET', path: '/orders/1001' });

await send('7. old key during rotation', {
  path: '/orders', body: order, keyId: 'client-1-2026-07', secret: 'demo-secret-key-2026-07' });

await send('8. retired key', {
  path: '/orders', body: order, keyId: 'client-1-2026-04', secret: 'demo-secret-key-2026-04' });

await send('9. wrong secret for a known keyId', {
  path: '/orders', body: order, secret: 'demo-secret-key-typo' });

await send('10. server verifies a re-serialized body (bug)', { path: '/buggy/orders', body: order });
