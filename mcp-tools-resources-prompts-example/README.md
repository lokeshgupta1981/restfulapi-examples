Source code for the article [MCP Tools vs Resources vs Prompts](https://restfulapi.net/mcp-tools-resources-prompts/)

# MCP tools, resources and prompts example

A travel-booking MCP server that offers all three server primitives, and a client that uses each one the way a host app would. Both speak MCP protocol version 2026-07-28 over stdio (one JSON-RPC message per line) and are written without an SDK, so every request and result body is visible in the code.

- `server.py` is the `travel-desk` server.
  - Tools are `get_booking` (with `outputSchema`, `structuredContent` and a `resource_link`) and `cancel_booking`, which asks the user to confirm with form elicitation. The elicitation uses the 2026-07-28 multi round-trip pattern, so the server returns an `InputRequiredResult` with an HMAC-signed `requestState`, and the client retries the call with `inputResponses`.
  - Resources are `docs://policies/cancellation` and the template `bookings://{booking_id}/receipt`.
  - The prompt is `draft_cancellation_reply` with the arguments `booking_id` and `tone`.
  - It checks the `_meta` fields on every request (there is no `initialize` in 2026-07-28) and answers `server/discover`.
- `client.py` starts `server.py` as a child process and calls every method, including the error cases. They are an unknown booking (`isError: true`), an unknown tool and an unknown resource (`-32602`), a call without the elicitation capability (`-32021`) and a retry with a changed `requestState`.

The signing key in `server.py` is a demo value. A real server loads it from its configuration.

## Versions

Python 3.10 or later (tested with Python 3.13). Only the standard library is used.

## Run

```bash
python3 client.py        # or ./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run. The `requestState` values change on every run because they contain an expiry time.
