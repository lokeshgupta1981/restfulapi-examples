// Three correct ways to read a commented config file in Node.js.
import { readFileSync } from 'node:fs';
import { parse, printParseErrorCode, stripComments } from 'jsonc-parser';
import stripJsonComments from 'strip-json-comments';
import JSON5 from 'json5';

const read = (name) => readFileSync(new URL("../config/" + name, import.meta.url), 'utf8');
const jsoncText = read('orders-service.jsonc');

// 1. jsonc-parser: the parser VS Code uses. It collects errors instead of throwing.
const errors = [];
const settings = parse(jsoncText, errors);
console.log('jsonc-parser:', JSON.stringify(settings), 'errors:', errors.length);

// Trailing commas are an error unless we allow them.
const trailingText = read('trailing-comma.jsonc');
const strictErrors = [];
parse(trailingText, strictErrors);
console.log('jsonc-parser trailing comma:', strictErrors.map((e) => printParseErrorCode(e.error) + ' at offset ' + e.offset));
const relaxedErrors = [];
parse(trailingText, relaxedErrors, { allowTrailingComma: true });
console.log('jsonc-parser allowTrailingComma:', relaxedErrors.length, 'errors');

// 2. Strip the comments, then use the normal JSON.parse().
const fromStripJson = JSON.parse(stripJsonComments(jsoncText));
const fromStripComments = JSON.parse(stripComments(jsoncText));
console.log('strip-json-comments:', fromStripJson.paymentUrl);
console.log('jsonc-parser stripComments:', fromStripComments.paymentUrl);

// 3. JSON5 reads JSONC files too, because JSON5 is a superset of JSONC.
console.log('json5 (.jsonc):', JSON.stringify(JSON5.parse(jsoncText)));
console.log('json5 (.json5):', JSON.stringify(JSON5.parse(read('orders-service.json5'))));
