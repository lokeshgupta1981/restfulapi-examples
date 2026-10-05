// Constant-time signature comparison for a Node.js server.
// Run: node compare.mjs
import { timingSafeEqual } from 'node:crypto';

function signaturesMatch(expectedHex, receivedHex) {
  const expected = Buffer.from(expectedHex, 'utf8');
  const received = Buffer.from(receivedHex, 'utf8');
  // timingSafeEqual throws a RangeError on different lengths, so check the length first
  return expected.length === received.length && timingSafeEqual(expected, received);
}

const signature = '9140e96dca095dfa3f4f13b237c07bb7cb5b116fcbf7c52d69665d12c40d066f';
console.log('same value:', signaturesMatch(signature, signature));
console.log('uppercase hex:', signaturesMatch(signature, signature.toUpperCase()));
console.log('first 10 characters:', signaturesMatch(signature, signature.slice(0, 10)));
