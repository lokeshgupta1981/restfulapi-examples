Source code for the article [JSON Lines (JSONL) and NDJSON Explained](https://restfulapi.net/json-lines-jsonl-ndjson/)

Small examples that write, read, validate and stream JSON Lines (JSONL) files with an orders data set:

- `write_jsonl.py` writes `data/orders.jsonl` and appends one more order.
- `read_jsonl.py` reads a JSONL file line by line; it stops at the first bad line, or skips bad lines with `--skip-bad`.
- `splitlines_bug.py` shows why `str.splitlines()` breaks JSONL that contains U+2028.
- `read_jsonl.mjs` reads a JSONL file with `node:readline` and reports bad lines.
- `batch_requests.py` builds and checks an OpenAI Batch API input file (`data/batch-input.jsonl`). It does not call the API. Set `BATCH_MODEL` to the model you want in the request bodies.
- `server.mjs` serves `GET /orders` (a JSON array) and `GET /orders/export` (JSONL, `Content-Type: application/jsonl`, one line every 200 ms).
- `client.py`, `client.mjs` and `src/` (Java, Maven) read the streamed response line by line.
- `demo.sh` runs every command; `OUTPUTS.txt` holds the output of one run.

## Versions

- Python 3.13, requests 2.34.2
- Node.js 22 (no dependencies)
- JDK 21, Maven 3.9, jackson-databind 2.22.3
- jq 1.7, curl 8.5.0

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/json-lines-jsonl-ndjson-example

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python write_jsonl.py            # creates data/orders.jsonl (server.mjs reads it)

# terminal 1: listens on 127.0.0.1:9387 (change with PORT=...)
node server.mjs

# terminal 2
python read_jsonl.py data/orders.jsonl
python read_jsonl.py data/orders-bad.jsonl --skip-bad
node read_jsonl.mjs data/orders-bad.jsonl
python splitlines_bug.py
python batch_requests.py
python client.py
node client.mjs
mvn -q compile exec:java -Dexec.args=http

# or everything at once
bash demo.sh
```
