Source code for the article [Base64 vs Base64URL](https://restfulapi.net/base64-vs-base64url/)

# Base64 vs Base64URL example

The same input (`<<???>>`, 7 bytes) encoded and decoded with standard Base64 (RFC 4648, section 4) and Base64URL (RFC 4648, section 5) in Python, Node.js, Java and Go, plus a small Orders API that uses each alphabet where real APIs use it.

- `python/encoding_demo.py`: alphabets, padding, size overhead, missing padding, the silent bug in `base64.b64decode()`, JWT segments.
- `python/api_server.py`: Orders API on `127.0.0.1:9170` (standard library only).
  - `GET /orders`: pagination cursor in Base64URL without padding.
  - `GET /legacy/orders`: the same cursor in standard Base64, which breaks when a client puts it into the query string without percent-encoding.
  - `POST /attachments`: file content in JSON as standard Base64; the response has a `Content-Digest` header (RFC 9530).
  - `GET /reports`: HTTP Basic authentication (RFC 7617), user `reports-app`, password `s3cret-42` (demo only).
- `demo.sh`: curl calls against the API, plus GNU `basenc` on the command line.
- `node/demo.mjs`: `Buffer`, `atob()`/`btoa()` and `Uint8Array.toBase64()`/`fromBase64()`.
- `java/Base64Demo.java`: `java.util.Base64` encoders and decoders.
- `go/main.go`: `encoding/base64` with `StdEncoding`, `URLEncoding` and `RawURLEncoding`.
- `decoder-matrix/`: the same five inputs (standard or URL-safe alphabet, with or without padding, one invalid character) fed to every decoder in Python, Node.js, Java and Go.

## Versions

- Python 3.13.16 (standard library only)
- Node.js 22.22.0 for `Buffer`, `atob()` and `btoa()`; Node.js 26.10.0 for `Uint8Array.toBase64()` (Node.js 25 or later)
- OpenJDK 21.0.12 (`java.util.Base64` exists since Java 8)
- Go 1.24.7
- curl 8, jq 1.7, GNU coreutils 9.4 (`base64`, `basenc`), OpenSSL 3

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/base64-vs-base64url-example

python3 python/encoding_demo.py

python3 python/api_server.py      # terminal 1, port 9170 (set PORT to change it)
./demo.sh                         # terminal 2 (set API_URL if you changed the port)

node node/demo.mjs                # section 3 needs Node.js 25 or later
java java/Base64Demo.java
(cd go && go run .)

python3 decoder-matrix/decoder_matrix.py
node decoder-matrix/decoder_matrix.mjs
java decoder-matrix/DecoderMatrix.java
(cd decoder-matrix/go && go run .)
```

`OUTPUTS.txt` holds the output of one run of every command above.
