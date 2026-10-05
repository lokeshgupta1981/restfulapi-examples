Source code for the article [OpenAPI Specification Tutorial: Write, Lint, Mock and Generate](https://restfulapi.net/openapi-specification-tutorial/)

One OpenAPI document for a small Orders API, plus the tools that use it: a linter, a docs build, a mock server and a generated TypeScript client.

## Versions

| Tool | Version |
|---|---|
| OpenAPI Specification (document) | 3.1.2 (`openapi.yaml`), 3.2.0 copy in `openapi-3.2.yaml` |
| Node.js | 22.22.0 |
| @redocly/cli (lint, docs) | 2.57.0 |
| @stoplight/prism-cli (mock server) | 5.16.0 |
| @openapitools/openapi-generator-cli | 2.41.0 (generator JAR 7.25.0, pinned in `openapitools.json`, needs Java 11+) |
| tsx / typescript | 4.23.15 / 5.9.3 |
| Python / FastAPI (code-first part) | 3.13 / 0.142.2 |

## Files

- `openapi.yaml`: the Orders API description (OpenAPI 3.1.2).
- `openapi-3.2.yaml`: the same document with `openapi: 3.2.0` and the 3.2 tag fields `summary` and `kind`.
- `openapi-broken.yaml`: a copy with common mistakes, for the lint demo.
- `redocly.yaml`: lint rules (recommended set plus stricter rules).
- `use-client.ts`: calls the mock server with the generated client.
- `code-first/main.py`: the same API written code-first with FastAPI.
- `run-all.sh`: runs every step below and prints the output.
- `OUTPUTS.txt`: output of one full run.

## Run

```bash
npm ci

# 1. Validate and lint
npx redocly lint openapi.yaml
npx redocly lint openapi-broken.yaml --format=stylish

# 2. Build HTML docs (Redoc) into docs/index.html
npx redocly build-docs openapi.yaml --output docs/index.html

# 3. Start the mock server on http://127.0.0.1:4010 (keep it running)
npx prism mock openapi.yaml

# 4. In a second terminal, call the mock
curl -i "http://127.0.0.1:4010/orders?status=pending" -H "Authorization: Bearer demo-token"
curl -i "http://127.0.0.1:4010/orders/ord_9999" -H "Authorization: Bearer demo-token" -H "Prefer: code=404"

# 5. Generate a TypeScript client and call the mock with it
npx openapi-generator-cli generate -i openapi.yaml -g typescript-fetch -o client
npx tsx use-client.ts

# 6. Code-first comparison (FastAPI)
cd code-first
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
cd ..
npx redocly lint code-first/generated-openapi.json --format=stylish
```

Or run everything at once (the mock server is started and stopped by the script, step 6 needs the venv from above):

```bash
./run-all.sh | tee OUTPUTS.txt
```
