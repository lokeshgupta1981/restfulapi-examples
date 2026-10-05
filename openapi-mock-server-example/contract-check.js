// Sends documented requests through a Prism validation proxy and fails
// when Prism reports a request or response that breaks openapi.yaml.
const proxyUrl = process.env.PROXY_URL ?? 'http://127.0.0.1:9224';

const checks = [
  { method: 'GET', path: '/orders' },
  { method: 'GET', path: '/orders/ord_1001' },
  { method: 'GET', path: '/orders/ord_9999' },
];

let failures = 0;
for (const check of checks) {
  const response = await fetch(proxyUrl + check.path, { method: check.method });
  const violations = JSON.parse(response.headers.get('sl-violations') ?? '[]');
  const label = check.method + ' ' + check.path + ' -> HTTP ' + response.status;
  if (violations.length === 0) {
    console.log('PASS ' + label);
    continue;
  }
  failures += 1;
  console.log('FAIL ' + label);
  for (const v of violations) {
    console.log('     ' + v.location.join('.') + ': ' + v.message);
  }
}
console.log((checks.length - failures) + ' passed, ' + failures + ' failed');
process.exitCode = failures === 0 ? 0 : 1;
