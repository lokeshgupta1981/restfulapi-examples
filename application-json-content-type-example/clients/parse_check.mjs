const url = 'http://127.0.0.1:9300/orders/1001';

// Naive client: calls res.json() without looking at the status or Content-Type.
try {
  const res = await fetch(url);
  const order = await res.json();
  console.log(order);
} catch (err) {
  console.log(`${err.name}: ${err.message}`);
}

// Safer client: checks the media type before parsing the body as JSON.
const res = await fetch(url);
const contentType = res.headers.get('content-type') ?? '';
const mediaType = contentType.split(';')[0].trim().toLowerCase();
const isJson = mediaType === 'application/json' || mediaType.endsWith('+json');
if (isJson) {
  console.log(await res.json());
} else {
  console.log('HTTP ' + res.status + ', expected JSON but got ' + contentType);
}
