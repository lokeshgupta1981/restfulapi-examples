// Client that sends the bearer token and refreshes it once on 401 invalid_token.
// Uses the short-lived-app client (2-second tokens) so the refresh path runs.
const TOKEN_URL = "http://localhost:4000/token";
const ORDERS_URL = "http://localhost:3000/orders";
const CLIENT_ID = "short-lived-app";
const CLIENT_SECRET = "short-lived-app-secret";

let accessToken = null;

async function fetchNewToken() {
  const response = await fetch(TOKEN_URL, {
    method: "POST",
    headers: {
      Authorization: "Basic " + Buffer.from(CLIENT_ID + ":" + CLIENT_SECRET).toString("base64"),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({ grant_type: "client_credentials", scope: "orders:read", resource: ORDERS_URL }),
  });
  const tokenResponse = await response.json();
  accessToken = tokenResponse.access_token;
  console.log("Got a new token, expires_in=" + tokenResponse.expires_in);
}

async function getOrders() {
  if (!accessToken) {
    await fetchNewToken();
  }
  let response = await fetch(ORDERS_URL, { headers: { Authorization: "Bearer " + accessToken } });
  const challenge = response.headers.get("www-authenticate") ?? "";
  if (response.status === 401 && challenge.includes('error="invalid_token"')) {
    console.log("HTTP 401: " + challenge);
    await fetchNewToken();
    response = await fetch(ORDERS_URL, { headers: { Authorization: "Bearer " + accessToken } });
  }
  if (!response.ok) {
    throw new Error("Orders request failed with HTTP " + response.status);
  }
  return response.json();
}

const first = await getOrders();
console.log("First call: " + first.orders.length + " orders");

// Wait until the 2-second token and the API's 5-second leeway have passed.
await new Promise((resolve) => setTimeout(resolve, 8000));

const second = await getOrders();
console.log("Second call: " + second.orders.length + " orders");
