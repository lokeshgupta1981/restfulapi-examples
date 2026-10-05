Source code for the article [Mock a REST API from an OpenAPI Document](https://restfulapi.net/openapi-mock-server/)

One OpenAPI 3.1 document (`openapi.yaml`, a small Orders API) served by three kinds of mock, plus a contract check of a real API through a validation proxy.

## Versions

- Node.js 22 (tested with 22.22.0)
- @stoplight/prism-cli 5.16.0
- @mockoon/cli 9.9.0
- openapi-backend 5.21.2
- curl for the manual calls

## Files

| File | What it does |
|---|---|
| `openapi.yaml` | The Orders API contract (OpenAPI 3.1.2) |
| `stateful-mock.js` | Stateful mock on port 9222: validates requests with openapi-backend and keeps orders in memory |
| `real-api.js` | A small "real" API on port 9223 with two contract bugs (start with `FIXED=1` for the fixed version) |
| `orders-client.js`, `consumer.test.js` | A client and its tests; `BASE_URL` picks the server |
| `contract-check.js` | Sends documented requests through a Prism proxy and fails on violations |
| `list-mockoon-routes.js` | Prints the routes Mockoon creates from `openapi.yaml` |
| `ci.sh`, `ci-workflow.yml` | The CI checks and a GitHub Actions workflow that runs them |
| `run-all.sh` | Runs every demo from the article in order |

## Run

```bash
npm ci

# Prism mock, static examples (port 9220)
npx prism mock openapi.yaml --port 9220

# Prism mock, generated data that repeats for the same seed
npx prism mock openapi.yaml --port 9220 --dynamic --seed orders

# Mockoon started from the same file (port 9221)
npx mockoon-cli start --data openapi.yaml --port 9221

# Stateful mock (port 9222)
node stateful-mock.js

# Consumer tests against any server
BASE_URL=http://127.0.0.1:9222 node --test consumer.test.js

# Contract check: real API behind a Prism validation proxy
node real-api.js &
npx prism proxy openapi.yaml http://127.0.0.1:9223 --port 9224
node contract-check.js

# Everything in one go, and the CI checks
./run-all.sh
bash ci.sh
FIXED=1 bash ci.sh
```

Ports 9220 to 9224 must be free. `run-all.sh` and `ci.sh` stop the servers they start.
