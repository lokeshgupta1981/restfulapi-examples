Source code for the article [Microsoft REST API Guidelines vs Google AIP and Zalando](https://restfulapi.net/rest-api-style-guides/)

The example compares three public REST API style guides on one small orders API:

- the Azure REST API Guidelines from Microsoft (`github.com/microsoft/api-guidelines`, folder `azure/`)
- Google's API Improvement Proposals (AIPs, `google.aip.dev`)
- the Zalando RESTful API and Event Guidelines (`opensource.zalando.com/restful-api-guidelines`)

It does two things:

1. `server.py` serves the same three orders in each style, so we can see the differences on the wire: versioning, field casing, pagination and error bodies.
2. `orders-api.yaml` is one OpenAPI document checked with a small Spectral ruleset per guide. Each rule names the guideline it checks and links to it. `rulesets/house.spectral.yaml` shows how a team builds its own guide from the three by extending the rulesets and switching rules off.

The rulesets are teaching subsets written for this article. They are not the official linters (Azure uses `@microsoft.azure/openapi-validator-rulesets`, Zalando uses Zally, Google's `api-linter` checks proto files).

## Files
- `server.py`: FastAPI app with three sub-apps mounted at `/azure`, `/google` and `/zalando`
- `demo.sh`: starts the server, sends the same requests to each style, follows the next-page link, stops the server
- `orders-api.yaml`: the orders API as many teams write it first (`/v1` paths, camelCase, `pageSize`/`pageToken`, a plain JSON error)
- `orders-api-house.yaml`: the same API after applying the house guide
- `rulesets/microsoft.spectral.yaml`, `rulesets/google.spectral.yaml`, `rulesets/zalando.spectral.yaml`: a few rules from each guide
- `rulesets/agreed.spectral.yaml`: two rules all three guides share
- `rulesets/house.spectral.yaml`: our own guide, built from the others
- `lint-all.sh`: lints `orders-api.yaml` with every ruleset, prints a summary, then lints both documents with the house ruleset
- `summary.mjs`: counts problems per rule from Spectral's JSON output
- `conflict.sh`: shows that `customerId` and `customer_id` cannot both pass all three guides
- `OUTPUTS.txt`: captured output of `demo.sh`, `lint-all.sh` and `conflict.sh`

## Versions
- Node.js 22.23.4, @stoplight/spectral-cli 6.17.0
- Python 3.13.18, FastAPI 0.143.0, uvicorn 0.54.0
- Guides as read on 2026-10-31 (Azure Guidelines change history ends 2026-Oct-22)

## How to run
```
npm install
./lint-all.sh
./conflict.sh

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PATH=.venv/bin:$PATH ./demo.sh          # port 8000, or PORT=9000 ./demo.sh
```

To lint one document with one guide:
```
npx spectral lint orders-api.yaml -r rulesets/zalando.spectral.yaml
```

On Windows, run the `npx spectral lint ...` commands from `lint-all.sh` one by one, and start the server with `python server.py`.
