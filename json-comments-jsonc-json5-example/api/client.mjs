// A client that calls the correct endpoint and the legacy one.
const base = process.env.BASE_URL ?? 'http://127.0.0.1:9185';

for (const path of ['/orders/42', '/legacy/orders/42']) {
  const response = await fetch(base + path);
  try {
    const order = await response.json();
    console.log(path, '->', response.status, JSON.stringify(order));
  } catch (error) {
    console.log(path, '->', response.status, error.name + ': ' + error.message);
  }
}
