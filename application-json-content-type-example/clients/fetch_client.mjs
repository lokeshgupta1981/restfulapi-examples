const url = 'http://127.0.0.1:9300/orders';
const order = { item: 'keyboard', quantity: 2 };

const noHeader = await fetch(url, {
  method: 'POST',
  headers: { 'X-Client': 'fetch, no Content-Type' },
  body: JSON.stringify(order),
});
console.log(await noHeader.text());

const withHeader = await fetch(url, {
  method: 'POST',
  headers: { 'X-Client': 'fetch, Content-Type set', 'Content-Type': 'application/json' },
  body: JSON.stringify(order),
});
console.log(await withHeader.text());

const objectBody = await fetch(url, {
  method: 'POST',
  headers: { 'X-Client': 'fetch, object body' },
  body: order,
});
console.log(await objectBody.text());
