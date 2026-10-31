Source code for the article [HTTP Message Signatures (RFC 9421) and Web Bot Auth](https://restfulapi.net/http-message-signatures/)

A small RFC 9421 implementation for Ed25519 (`httpsig.py`), checked against the published test vectors, plus a complete Web Bot Auth setup: a bot that signs its requests, the bot's signed key directory, and a Bookstore API that verifies the signatures. It also verifies the real signed key directory that ChatGPT agent publishes, and sends signed requests to Cloudflare Research's public demo server.

All keys in `keys/` are demo or test keys. `rfc9421-test-key-ed25519.json` is the published test key from RFC 9421 Appendix B.1.4, and `demo-bot-key.json` was generated for this example and is public in this repository. Never use either for anything real.

## Versions

- Python 3.13, FastAPI 0.143.0 (Starlette 1.7.0), uvicorn 0.54.0, httpx 0.28.1, cryptography 50.0.2, http-sfv 0.9.9
- curl 8.5.0
- Specs: RFC 9421, RFC 9530 (Content-Digest), draft-ietf-webbotauth-httpsig-protocol-01 (29 October 2026)

## Files

| File | What it does |
|---|---|
| `httpsig.py` | Signature base, Ed25519 signing and verifying, `;key=` and `;req` component parameters, Content-Digest, JWK thumbprint |
| `test_vectors.py` | Reproduces RFC 9421 test case B.2.6 and Web Bot Auth draft test vector E.2.1 byte for byte |
| `verify_directory.py` | Verifies ChatGPT agent's signed key directory (snapshot in `snapshots/`, or `--live`) |
| `bot_directory.py` | The bot operator's key directory at `/.well-known/http-message-signatures-directory`, signed with `tag="http-message-signatures-directory"` |
| `server.py` | Bookstore API that verifies Web Bot Auth signatures: Accept-Signature, coverage policy, created/expires, directory fetch and cache, keyid lookup, Content-Digest check |
| `bot.py` | The signing bot; runs eleven success and failure scenarios against `server.py` |
| `live_cloudflare_demo.py` | Signs requests with the RFC test key and sends them to Cloudflare Research's demo server |
| `run_all.sh` | Runs everything; its output is in `OUTPUTS.txt` |

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/http-message-signatures-example

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Everything at once (starts and stops both servers; ports 8000 and 8001)
./run_all.sh
```

Or step by step:

```bash
python test_vectors.py
python verify_directory.py            # add --live to check today's directory

uvicorn bot_directory:app --port 8001 # terminal 1: the bot's key directory
uvicorn server:app --port 8000        # terminal 2: the Bookstore API
python bot.py                         # terminal 3: eleven scenarios

python live_cloudflare_demo.py        # needs internet access
```

Use other ports with `ORIGIN_PORT=9000 DIRECTORY_PORT=9001 ./run_all.sh`, or set `ORIGIN` and `AGENT_URL` for `bot.py`. `OUTPUTS.txt` was captured on ports 20030 and 20031.

Timestamps, nonces and signatures in your output differ from `OUTPUTS.txt`, because the bot signs with the current time and random nonces. The test vector signatures are always the same, because Ed25519 signatures are deterministic.

The directory runs on plain http for this local demo. Web Bot Auth requires https for key directories, and `server.py` allows http only for `127.0.0.1` and `localhost`.
