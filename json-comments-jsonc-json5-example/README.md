Source code for the article [Comments in JSON: JSONC and JSON5](https://restfulapi.net/json-comments-jsonc-json5/)

One orders-service config file written three ways (JSONC, JSON5 and plain JSON with comment keys), read by strict and comment-aware parsers in Python, Node.js, Java and Go, plus a small orders API that rejects a request body with a comment.

## Versions

- Python 3.13 with json5 0.15.0 and jsonschema 4.26.0 (`requirements.txt`); `api/server.py` uses only the standard library
- Node.js 22 with json5 2.2.3, jsonc-parser 3.3.1 and strip-json-comments 5.0.3 (`node/package.json`)
- TypeScript 7.0.2 (`tsconfig-demo/package.json`)
- JDK 21, Maven 3.9 and Jackson 3.2.3 (`tools.jackson.core:jackson-databind`, `java/pom.xml`)
- Go 1.24 (standard library only)
- jq 1.7 and curl 8.5.0 for the command-line checks

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/json-comments-jsonc-json5-example

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
(cd node && npm ci)
(cd tsconfig-demo && npm ci)

bash demo.sh
```

The script `demo.sh` runs every demo in order and starts the orders API on 127.0.0.1:9185 for the last part. To run the API alone:

```bash
python api/server.py            # PORT=... to change the port
curl -i -X POST http://127.0.0.1:9185/orders -H 'Content-Type: application/json' \
  --data-binary $'{\n  "items": [ { "sku": "BOOK-1", "qty": 2 } ] // gift wrap\n}'
node api/client.mjs
```

## Files

- `config/orders-service.jsonc`: the config as JSON with Comments
- `config/orders-service.json5`: the same config as JSON5 (unquoted keys, single quotes, trailing commas, a hex number)
- `config/orders-service-comment-keys.json`: plain JSON with `"_comment"` and duplicate `"//"` keys
- `config/orders-service.schema.json`: a JSON Schema with `additionalProperties: false`
- `config/trailing-comma.jsonc`: a file whose only problem is a trailing comma
- `python/`: strict `json` errors, loading with `json5`, a wrong regex stripper, the costs of comment keys
- `node/`: `JSON.parse()` errors, then `jsonc-parser`, `strip-json-comments` and `json5`
- `java/`: Jackson 3 with and without `JsonReadFeature.ALLOW_JAVA_COMMENTS`
- `go/`: the `encoding/json` errors
- `tsconfig-demo/`: `tsc --showConfig` reads a `tsconfig.json` with comments and trailing commas
- `api/`: `server.py` (orders API) and `client.mjs` (a `fetch()` client)

`OUTPUTS.txt` holds the output of one full run.
