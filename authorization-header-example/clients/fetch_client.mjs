// Node.js fetch(): Basic auth by hand, Bearer header and redirects.
const basicValue = 'Basic ' + Buffer.from('reports-app:demo-pass-123', 'utf8').toString('base64');
const response = await fetch('http://127.0.0.1:9771/echo', {
  headers: { Authorization: basicValue }
});
console.log('Basic by hand  ', (await response.json()).authorization);

for (const target of ['to-same', 'to-port', 'to-host']) {
  const redirected = await fetch('http://127.0.0.1:9771/' + target, {
    headers: { Authorization: 'Bearer demo-token-123' }
  });
  const body = await redirected.json();
  console.log('redirect ' + target.padEnd(8), body.host, body.authorization);
}
