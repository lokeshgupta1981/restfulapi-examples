// Header parsing helpers used by server.js.
import { timingSafeEqual } from 'node:crypto';
import { parse as parseBasic } from 'basic-auth';

export { parseBasic };

// Bearer scheme in any case, one or more spaces, then a token68 value.
const BEARER = /^Bearer +([A-Za-z0-9\-._~+/]+=*) *$/i;

export function bearerToken(value) {
  const match = BEARER.exec(value ?? '');
  return match ? match[1] : null;
}

// Compares two secrets in constant time.
export function safeEqual(a, b) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

// Returns the scheme name for a log line, never the credentials.
export function schemeForLog(value) {
  if (!value) return '-';
  const match = /^([A-Za-z][A-Za-z0-9._~+-]{0,19}) /.exec(value);
  return match ? match[1] : '(malformed)';
}
