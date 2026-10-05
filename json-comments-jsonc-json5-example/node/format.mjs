// Pretty-prints JSONC and keeps the comments (the VS Code formatter uses the same library).
import { applyEdits, format } from 'jsonc-parser';

const compact = '{"port":8080, // HTTP port\n"retry":{"maxAttempts":3,/* per request */"backoffMs":200}}';
const edits = format(compact, undefined, { tabSize: 2, insertSpaces: true, eol: '\n' });
const pretty = applyEdits(compact, edits);
console.log(pretty);
