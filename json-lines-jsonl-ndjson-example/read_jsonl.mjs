// Read a JSON Lines file line by line with node:readline.
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';

const path = process.argv[2] ?? 'data/orders.jsonl';
const lines = createInterface({ input: createReadStream(path, 'utf8'), crlfDelay: Infinity });

let lineNo = 0;
let count = 0;
for await (const line of lines) {
  lineNo += 1;
  if (line.trim() === '') continue;
  try {
    const order = JSON.parse(line);
    count += 1;
    console.log(lineNo, order.id, order.customer);
  } catch (err) {
    console.error('line ' + lineNo + ': ' + err.message);
  }
}
console.log(count + ' orders read');
