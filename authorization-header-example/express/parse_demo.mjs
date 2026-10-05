import { bearerToken, parseBasic, schemeForLog } from './auth.js';

console.log(parseBasic('basic cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw=='));
console.log(parseBasic('Basic  cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw'));
console.log(bearerToken('bearer demo-token-123'));
console.log(bearerToken('Bearerdemo-token-123'));

// Wrong: a value without a space has no first word, so all of it is returned.
const naiveScheme = (value) => value.split(' ')[0];
console.log(naiveScheme('BasiccmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw=='));
console.log(schemeForLog('BasiccmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw=='));
console.log(schemeForLog('Bearer demo-token-123'));
