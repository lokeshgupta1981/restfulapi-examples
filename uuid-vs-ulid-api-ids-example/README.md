Source code for the article [UUIDv7 vs ULID vs UUIDv4 for API IDs](https://restfulapi.net/uuid-vs-ulid-api-ids/)

# UUIDv7 vs ULID vs UUIDv4 for API IDs example

A small Orders API that can use UUIDv4, UUIDv7 or ULID as its order IDs, plus two scripts that check what each kind of ID shows in a REST API: length, sort order, the creation time inside the ID, guessable neighbours, cursor pagination and client-generated IDs.

- `ids.py`: create, validate (`parse_id()`) and inspect (`created_at()`) the three kinds of IDs. UUIDv4 and UUIDv7 come from Python's `uuid` module, ULID from `python-ulid`.
- `sample_ids.py`: sample IDs, the timestamp inside UUIDv7 and ULID, sort order of 10,000 IDs, same-millisecond neighbours, guessing the next ULID, the same 128 bits written as a UUID and as a ULID.
- `store.py`: an in-memory SQLite table with the ID as the primary key and keyset pagination (`WHERE id > ? ORDER BY id`).
- `pagination_race.py`: a client pages through 10 orders, 3 per page, while a new order is created; counts how often the client never sees it (1,000 runs per kind).
- `server.py`: FastAPI Orders API. `ID_KIND` selects `uuid7` (default), `uuid4` or `ulid`; `PORT` defaults to 8000.
  - `POST /orders`: the server creates the ID (201 with `Location`).
  - `PUT /orders/{id}`: the client creates the ID. 201 the first time, 200 for the same retry, 409 for the same ID with a different body, 400 for a malformed or wrong-version ID, 422 for a UUIDv7 dated in the future. Errors use RFC 9457 problem details.
  - `GET /orders/{id}`: accepts either letter case.
  - `GET /orders?limit=3&after=<id>`: keyset pagination with the last ID as the cursor.
- `id_tool.py`: command line helper used by `demo.sh` (new ID, future-dated UUIDv7, creation time of an ID).
- `demo.sh`: curl calls against the server.

## Versions

- Python 3.14.6 (`uuid.uuid7()` needs Python 3.14 or later)
- python-ulid 4.1.0, FastAPI 0.162.0, uvicorn 0.54.0
- curl 8, jq 1.7

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/uuid-vs-ulid-api-ids-example
python3.14 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python sample_ids.py
python pagination_race.py

ID_KIND=uuid7 python server.py     # terminal 1 (also try ulid and uuid4; set PORT to change the port)
ID_KIND=uuid7 ./demo.sh            # terminal 2 (set API_URL if you changed the port)
```

`OUTPUTS.txt` holds the output of one run of every command above.
