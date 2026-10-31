// The same inventory call, protected by the opossum circuit breaker library (Node.js).
// Start inventory_service.py on port 9601 first, then: node opossum_demo.js
const CircuitBreaker = require('opossum');

const INVENTORY = 'http://127.0.0.1:9601';

async function fetchStock(bookId) {
  const res = await fetch(`${INVENTORY}/stock/${bookId}`);
  if (res.status >= 500) throw new Error(`inventory answered ${res.status}`);
  return (await res.json()).in_stock;
}

const breaker = new CircuitBreaker(fetchStock, {
  timeout: 2000,                 // a call slower than 2 s counts as a failure
  errorThresholdPercentage: 50,  // open when half of the recent calls failed...
  volumeThreshold: 5,            // ...but only after at least 5 calls
  resetTimeout: 5000             // stay open for 5 s, then let one trial call through
});

breaker.fallback(() => null);   // the book page shows "stock unknown"
for (const event of ['open', 'halfOpen', 'close']) {
  breaker.on(event, () => console.log(`  event: ${event}`));
}
breaker.on('reject', () => console.log('  event: reject (inventory not called)'));

const setMode = (mode) => fetch(`${INVENTORY}/admin/mode?mode=${mode}`, { method: 'POST' })
  .then(() => console.log(`[inventory mode: ${mode}]`));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  await setMode('healthy');
  console.log('call 1 ->', await breaker.fire(1));
  await setMode('down');
  for (let i = 2; i <= 8; i++) {
    console.log(`call ${i} ->`, await breaker.fire(1), `(state: ${breaker.opened ? 'open' : 'closed'})`);
  }
  // Without a fallback, a rejected call fails with an error code we can check:
  const noFallback = new CircuitBreaker(fetchStock, { resetTimeout: 5000 });
  noFallback.open();
  await noFallback.fire(1).catch((e) => console.log(`no fallback -> ${e.code}: ${e.message}`));
  noFallback.shutdown();

  await setMode('healthy');
  console.log('waiting 5 s...');
  await sleep(5100);
  console.log('call 9 ->', await breaker.fire(1));
  const s = breaker.stats;
  console.log(`stats: fires=${s.fires} successes=${s.successes} failures=${s.failures} rejects=${s.rejects} fallbacks=${s.fallbacks}`);
  breaker.shutdown();
}

main();
