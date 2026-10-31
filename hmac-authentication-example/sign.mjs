// The same canonical request, signature and constant-time compare in Node.js.
// Run: node sign.mjs  (Node.js 22, no packages)
import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

const SECRET = 'demo-secret-key-2026-10'; // example value, not a real key

// encodeURIComponent() leaves !'()* alone; RFC 3986 encoding needs them encoded
function rfc3986(text) {
  return encodeURIComponent(text).replace(/[!'()*]/g,
    (c) => '%' + c.charCodeAt(0).toString(16).toUpperCase());
}

function canonicalQuery(rawQuery) {
  const pairs = [...new URLSearchParams(rawQuery)];
  pairs.sort((a, b) => (a[0] === b[0] ? (a[1] < b[1] ? -1 : 1) : (a[0] < b[0] ? -1 : 1)));
  return pairs.map(([name, value]) => rfc3986(name) + '=' + rfc3986(value)).join('&');
}

function canonicalRequest(method, host, path, rawQuery, timestamp, nonce, body) {
  const bodyHash = createHash('sha256').update(body).digest('hex');
  return [method.toUpperCase(), host.toLowerCase(), path, canonicalQuery(rawQuery),
    timestamp, nonce, bodyHash].join('\n');
}

function sign(secret, canonical) {
  return createHmac('sha256', secret).update(canonical, 'utf8').digest('hex');
}

function signaturesMatch(expectedHex, receivedHex) {
  const expected = Buffer.from(expectedHex, 'utf8');
  const received = Buffer.from(receivedHex, 'utf8');
  // timingSafeEqual throws a RangeError on different lengths, so check the length first
  return expected.length === received.length && timingSafeEqual(expected, received);
}

const canonical = canonicalRequest('POST', 'localhost:9410', '/orders',
  'note=gift+wrap&currency=USD', '1791200000', 'n-0001', '{"item":"keyboard","quantity":2}');
const signature = sign(SECRET, canonical);
console.log(canonical);
console.log('signature: ' + signature);
console.log('same value:', signaturesMatch(signature, signature));
console.log('uppercase hex:', signaturesMatch(signature, signature.toUpperCase()));
console.log('first 10 characters:', signaturesMatch(signature, signature.slice(0, 10)));
