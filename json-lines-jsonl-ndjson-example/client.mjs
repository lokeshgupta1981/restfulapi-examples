// Read a streamed JSONL response with fetch(), splitting chunks into lines.
const start = performance.now();
const response = await fetch('http://127.0.0.1:9387/orders/export');
console.log('Content-Type:', response.headers.get('content-type'));

const decoder = new TextDecoder();
let buffer = '';

function handleLine(line) {
  if (line.trim() === '') return;
  const order = JSON.parse(line);
  const seconds = ((performance.now() - start) / 1000).toFixed(1);
  console.log(seconds + 's ' + order.id + ' ' + order.status);
}

for await (const chunk of response.body) {
  buffer += decoder.decode(chunk, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop(); // keep the incomplete last line for the next chunk
  lines.forEach(handleLine);
}
buffer += decoder.decode();
handleLine(buffer);
