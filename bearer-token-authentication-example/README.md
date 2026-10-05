Source code for the article [Bearer Token Authentication in REST APIs](https://restfulapi.net/bearer-token-authentication/)

# Bearer token authentication example

A small Orders API (Express) that accepts JWT bearer tokens, plus a tiny demo token issuer.

- `issuer.js`: demo authorization server on port 4000. It supports the OAuth 2.0 client credentials grant, signs RS256 JWT access tokens (`typ: at+jwt`) and publishes its public key at `/.well-known/jwks.json`. Demo only.
- `api.js`: Orders API on port 3000. `GET /orders` needs a bearer token with `aud` = `http://localhost:3000/orders` and the scope `orders:read`. It checks the signature, `iss`, `aud`, `exp` and `typ`, and answers with HTTP 400, 401 or 403 plus a `WWW-Authenticate: Bearer ...` challenge (RFC 6750).
- `demo.sh`: curl calls for the main cases (no token, Basic credentials, malformed header, token that is not a JWT, token in the query string, wrong audience, missing scope, valid token, lowercase scheme, expired token, issuer keys unreachable). Needs curl and jq.
- `client.js`: a client that sends the bearer token with `fetch()` and gets a new token once when the API answers HTTP 401 with `error="invalid_token"`.

The API reads the token from the `Authorization` header and rejects `access_token` in the query string. It does not read the form body (RFC 6750, section 2.2), because `GET /orders` has no body.

When the API cannot load the issuer's keys (issuer down, timeout, bad JWKS response), it answers HTTP 503 with `Retry-After` and no `WWW-Authenticate`, so clients do not refresh their token in a loop.

## Versions

- Node.js 22.22.0 (any Node.js 22 or later)
- express 5.2.1
- jose 6.2.12
- curl and jq 1.7 (for `demo.sh`)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/bearer-token-authentication-example
npm ci
node issuer.js        # terminal 1
node api.js           # terminal 2
./demo.sh             # terminal 3
node client.js        # terminal 3
```

Get a token by hand:

```bash
curl -s -u orders-app:orders-app-secret \
  -d grant_type=client_credentials \
  -d scope=orders:read \
  --data-urlencode resource=http://localhost:3000/orders \
  http://localhost:4000/token
```

Keep the token in a shell variable and call the API:

```bash
ORDERS_TOKEN=$(curl -s -u orders-app:orders-app-secret -d grant_type=client_credentials \
  -d scope=orders:read --data-urlencode resource=http://localhost:3000/orders \
  http://localhost:4000/token | jq -r .access_token)
curl -i -H "Authorization: Bearer $ORDERS_TOKEN" http://localhost:3000/orders
```

## Demo clients

| Client | Secret | Scopes | Token lifetime |
|---|---|---|---|
| orders-app | orders-app-secret | orders:read orders:write | 300 s |
| reports-app | reports-app-secret | reports:read | 300 s |
| short-lived-app | short-lived-app-secret | orders:read | 2 s |

The secrets and the in-memory signing key are for the demo only. In production, use a real authorization server and keep secrets out of source code.
