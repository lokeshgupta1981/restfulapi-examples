Source code for the article [Base64 vs Base64URL: Differences and When to Use Each](https://restfulapi.net/base64-vs-base64url/)

# Base64 vs Base64URL example

A small Orders API (FastAPI) that uses standard Base64 (RFC 4648, section 4) and Base64URL (RFC 4648, section 5) where real APIs use them, curl and httpx clients that show what breaks, and the same input (`<<???>>`, 7 bytes) encoded and decoded in Python, Node.js, Java and Go.

- `server.py`: Orders API on `127.0.0.1:9170`.
  - `GET /orders`: pagination cursor in Base64URL without padding, signed with an HMAC.
  - `GET /legacy/orders`: the same cursor in standard Base64, which breaks when a client puts it into the query string without percent-encoding.
  - `POST /attachments`: file content in JSON as standard Base64; the response has a `Content-Digest` header (RFC 9530).
  - `GET /reports`: HTTP Basic authentication (RFC 7617).
- `client.py`: httpx follows the legacy cursor with an f-string URL (HTTP 400) and with `params=` (HTTP 200), then the Base64URL cursor.
- `demo.sh`: curl calls against the API, plus GNU `basenc` on the command line.
- `encoding_demo.py`: alphabets, padding, size overhead, missing padding, the silent bug in `base64.b64decode()`, JWT segments.
- `node/demo.mjs`: `Buffer`, `atob()`/`btoa()` and `Uint8Array.toBase64()`/`fromBase64()`.
- `java/Base64Demo.java`: `java.util.Base64` encoders and decoders.
- `go/main.go`: `encoding/base64` with `StdEncoding`, `URLEncoding` and `RawURLEncoding`.
- `decoder-matrix/`: the same five inputs (standard or URL-safe alphabet, with or without padding, one invalid character) fed to every decoder in Python, Node.js, Java and Go.
- `pixel.png`: a 70-byte PNG for the upload demo.
- `run_all.sh`: starts the server, runs every demo and every command used in the article, and stops the server. `OUTPUTS.txt` holds one captured run.

All credentials and keys are demo values for local tests only: user `reports-app`, password `s3cret-42`, cursor key `cursor-demo-key`, JWT key `demo-signing-key`.

## Versions

- Python 3.13 (3.10 or later works), fastapi 0.142.2, uvicorn 0.54.0, httpx 0.28.1
- Node.js 22.23.4 for `Buffer`, `atob()` and `btoa()`; Node.js 26.13.0 for `Uint8Array.toBase64()` and `fromBase64()` (Node.js 25 or later)
- OpenJDK 25.0.4.1 (`java.util.Base64` exists since Java 8)
- Go 1.24.7
- curl 8.5.0, jq 1.7, GNU coreutils 9.4 (`base64`, `basenc`)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/base64-vs-base64url-example
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

uvicorn server:app --host 127.0.0.1 --port 9170   # terminal 1
./demo.sh                                         # terminal 2
python3 client.py

python3 encoding_demo.py
node node/demo.mjs                # section 3 needs Node.js 25 or later
java java/Base64Demo.java
(cd go && go run .)

python3 decoder-matrix/decoder_matrix.py
node decoder-matrix/decoder_matrix.mjs
java decoder-matrix/DecoderMatrix.java
(cd decoder-matrix/go && go run .)
```

Or run everything at once (stop the server from terminal 1 first). Set `NODE` to a Node.js 25+ binary for the `fromBase64()` parts:

```bash
NODE=node ./run_all.sh > OUTPUTS.txt
```
