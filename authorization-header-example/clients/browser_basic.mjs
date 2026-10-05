// Basic credentials with btoa() and TextEncoder, the APIs a browser has.
// Node.js 22 has the same globals, so this file runs with: node browser_basic.mjs

function basicHeader(user, password) {
  const bytes = new TextEncoder().encode(user + ':' + password);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return 'Basic ' + btoa(binary);
}

console.log(basicHeader('reports-app', 'demo-pass-123'));
console.log('UTF-8 via encoder   ', basicHeader('reports-app', 'demo-café-123'));
console.log('btoa() on the text  ', 'Basic ' + btoa('reports-app:demo-café-123'));
try {
  btoa('reports-app:demo-€-123');
} catch (error) {
  console.log('btoa() with a euro sign throws', error.name);
}
