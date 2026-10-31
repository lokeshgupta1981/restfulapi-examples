Source code for the article [Client ID Metadata Documents vs Dynamic Client Registration](https://restfulapi.net/cimd-vs-dynamic-client-registration/)

One demo authorization server supports both ways for an OAuth client to get a `client_id` without a manual sign-up:

- Dynamic Client Registration (RFC 7591): the client POSTs its metadata to `/register` and gets a new `client_id` back.
- Client ID Metadata Documents (draft-ietf-oauth-client-id-metadata-document-02): the client hosts a JSON document at an https URL and uses that URL as its `client_id`. The server fetches, validates and caches it.

Files:

- `auth_server.py`: the authorization server (default port 9000). Metadata advertises `registration_endpoint` and `client_id_metadata_document_supported`. `/authorize` and `/token` implement the authorization code flow with PKCE (S256) for public clients. The CIMD fetch checks the URL rules, blocks non-public addresses (SSRF), does not follow redirects, reads at most 5 KB, checks that `client_id` matches the URL and that there is no client secret, and caches the document for its `max-age`. `/demo/stats` shows how many DCR registrations and CIMD documents the server holds.
- `client_site.py`: the client's website over https (default port 8443). It serves `/oauth/client-metadata.json` plus broken documents for the demo (copied, with a secret, behind a redirect, too large).
- `make_cert.py`: creates a self-signed certificate for `localhost` in `certs/`.
- `client.py`: a public client (think MCP client) that picks pre-registration, then CIMD, then DCR, as the MCP 2026-07-28 spec recommends, and then gets a token. DCR registrations are stored per issuer in `dcr_registrations.json`.
- `demo.sh`: the comparison with curl.
- `OUTPUTS.txt`: output of a real run.

Not for production: no login or consent page (the demo user always approves), everything is in memory, the authorization server runs on plain http on 127.0.0.1, and `CIMD_ALLOW_LOOPBACK=1` lets the server fetch a document from `localhost`. The draft allows that exception only for development and testing.

## Versions

- Python 3.13.18 (3.10 or newer works)
- FastAPI 0.143.0, Uvicorn 0.54.0, httpx 0.28.1, python-multipart 0.0.32, cryptography 50.0.2

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python make_cert.py

# terminal 1 (development settings: allow localhost, trust our certificate)
CIMD_ALLOW_LOOPBACK=1 CIMD_CA_FILE=certs/localhost.pem python auth_server.py

# terminal 2
python client_site.py

# terminal 3
./demo.sh
python client.py http://127.0.0.1:9000          # auto: uses CIMD
python client.py http://127.0.0.1:9000 dcr      # forces DCR, run twice to see the stored registration
```

Ports are configurable: `AS_PORT`, `CLIENT_SITE_PORT`, `CLIENT_CALLBACK`, and for the client and demo `CLIENT_METADATA_URL`, `AS`, `SITE`, `CB`. `OUTPUTS.txt` was captured with the authorization server on 29880, the client site on 29881 and the callback on 29882.

Start the authorization server without `CIMD_ALLOW_LOOPBACK=1` to see the SSRF guard refuse `https://localhost:...` (run 5 in `OUTPUTS.txt`).
