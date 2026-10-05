Source code for the article [PUT vs PATCH in REST APIs](https://restfulapi.net/put-vs-patch/)

# PUT vs PATCH example

A small Tickets API in Python (FastAPI) with one resource, `/tickets/{id}`, that accepts both methods:

- `PUT` replaces the whole ticket. The response carries the new `ETag` only when the stored ticket equals the body as sent (RFC 9110, section 9.3.4). Every field except `assignee` is required, so a body with missing fields gets HTTP 422 instead of erasing data. A `PUT` to a new id creates the ticket (HTTP 201 with `Location`). Sending the same `PUT` twice leaves the ticket and its `ETag` unchanged.
- `PATCH` accepts `application/merge-patch+json` (RFC 7396) and `application/json-patch+json` (RFC 6902). Any other `Content-Type` gets HTTP 415 with an `Accept-Patch` header. The server validates the patched result before it stores anything.
- Every write supports `If-Match`. A stale `ETag` gets HTTP 412. Start the server with `REQUIRE_IF_MATCH=true` to reject writes without `If-Match` (HTTP 428).
- Errors use Problem Details (`application/problem+json`, RFC 9457).

Data lives in memory and resets when the server restarts.

## Files

- `app.py`: the API.
- `put.sh`: PUT cases (full PUT, retried PUT, PUT with one field, PUT that creates, PUT without the optional `assignee` field).
- `patch.sh`: PATCH cases (merge patch, `null` in a merge patch, invalid result, wrong media type, OPTIONS, missing ticket, JSON Patch append retried without and with `If-Match`).
- `lost_update.sh`: two clients send PUT from the same old copy; the first change is lost.
- `lost_update_patch.sh`: the same edits as merge patches, on different fields and on the same field.
- `if_match.sh`: the two PUTs from `lost_update.sh`, both with `If-Match`; the second gets HTTP 412.
- `client.py`: a client that raises the priority with PUT and `If-Match`, gets HTTP 412 and retries after a new GET (standard library only).
- `defaults_pitfall.py`: shows how a Pydantic model with default values turns a partial PUT body into a full replacement that erases fields, and how `exclude_unset=True` keeps a PATCH partial.
- `OUTPUTS.txt`: output of all scripts from a real run.

Each script and `client.py` expects the starting ticket, so restart the server before each one.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.142.2, uvicorn 0.54.0, pydantic 2.13.5, jsonpatch 1.33, jsonpointer 3.1.1 (pinned in `requirements.txt`)
- curl (for the shell scripts)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/put-vs-patch-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app:app --port 9110        # terminal 1
./put.sh                           # terminal 2
```

Restart the server (Ctrl+C, then the same uvicorn command) before each of `patch.sh`, `lost_update.sh`, `lost_update_patch.sh`, `if_match.sh` and `client.py`.

To make `If-Match` mandatory (HTTP 428 without it):

```bash
REQUIRE_IF_MATCH=true uvicorn app:app --port 9110
curl -si -X PATCH http://localhost:9110/tickets/TCK-1001 \
  -H 'Content-Type: application/merge-patch+json' -d '{"status": "closed"}'
```

To use another port, start uvicorn with `--port 8000` and run the scripts with `BASE=http://localhost:8000`.
