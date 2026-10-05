"""Runs one tool call against the Orders API and returns a result the model can act on."""
import json
import time
import uuid

import httpx
from jsonschema import Draft202012Validator

from tools import OPERATIONS, SCHEMAS

MAX_RESULT_CHARS = 4000
MAX_ATTEMPTS = 2  # one retry after a timeout, with the same Idempotency-Key on writes
# Any fixed UUID works; uuid5 needs a namespace to derive keys from tool call ids.
KEY_NAMESPACE = uuid.UUID("6f1c2b1e-9a43-4a8e-8f0e-3d1f0c6b7a52")


def error_result(error: str, message: str, retryable: bool, **extra) -> dict:
    return {"ok": False, "error": error, "message": message, "retryable": retryable, **extra}


def map_http_response(response: httpx.Response) -> dict:
    """Turn an HTTP response into a small JSON result for the model."""
    status = response.status_code
    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text[:300]}
    detail = body.get("detail", "") if isinstance(body, dict) else ""

    if 200 <= status < 300:
        result = {"ok": True, "status": status, "data": body}
        if response.headers.get("Idempotent-Replayed") == "true":
            result["replayed"] = True  # the API returned the stored response of an earlier attempt
        return result
    if status == 404:
        return error_result("not_found", detail, False, status=404,
                            hint="Check the ID with the user. Do not guess another ID.")
    if status == 409:
        return error_result("conflict", detail, False, status=409,
                            hint="Explain the current state to the user. Do not retry.")
    if status in (400, 422):
        return error_result("invalid_request", json.dumps(detail)[:300], False, status=status,
                            hint="Fix the arguments or ask the user for the missing value.")
    if status in (401, 403):
        return error_result("not_allowed", "The API refused this call.", False, status=status)
    if status == 429:
        retry_after = response.headers.get("Retry-After", "60")
        return error_result("rate_limited", detail, True, status=429,
                            retry_after_seconds=int(retry_after) if retry_after.isdigit() else 60,
                            hint="Tell the user to try again later. Do not call this tool again in this turn.")
    if status >= 500:
        return error_result("upstream_error", f"The Orders API failed with HTTP {status}.", True, status=status)
    return error_result("http_error", detail, False, status=status)


def execute_tool_call(client: httpx.Client, call_id: str, name: str, raw_arguments: str,
                      confirm) -> dict:
    # 1. Allow list: only operations we mapped by hand can run.
    operation = OPERATIONS.get(name)
    if operation is None:
        return error_result("unknown_tool", f"There is no tool named {name}.", False)

    # 2. Arguments arrive as a JSON string. Parse and validate them against the schema.
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return error_result("invalid_arguments", "Arguments are not valid JSON.", False)
    errors = [e.message for e in Draft202012Validator(SCHEMAS[name]).iter_errors(arguments)]
    if errors:
        return error_result("invalid_arguments", "; ".join(errors), False,
                            hint="Ask the user for a valid value. Do not invent one.")

    # 3. Writes need a yes from the user before the HTTP call.
    if operation["write"] and not confirm(name, arguments):
        return error_result("declined_by_user", "The user did not confirm this action.", False)

    path = operation["path"].format(**arguments)
    headers = {}
    body = None
    if operation["write"]:
        # Same tool call id -> same key, so a retry of this call cannot cancel twice.
        headers["Idempotency-Key"] = str(uuid.uuid5(KEY_NAMESPACE, call_id))
        body = {field: arguments[field] for field in operation.get("body", [])}

    # 4. Call the API with a timeout. Retry once after a timeout: the retry of a write
    #    sends the same Idempotency-Key, so the API cannot apply the change twice.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.request(operation["method"], path, json=body, headers=headers)
            break
        except httpx.TimeoutException:
            if attempt == MAX_ATTEMPTS:
                # A new tool call would get a new key, so the model must not retry a write.
                return error_result("timeout", "The Orders API did not answer in time.",
                                    retryable=not operation["write"])
            print(f"[retry] {name} timed out, sending it again with the same headers")
            time.sleep (0.2)
        except httpx.TransportError as exc:
            return error_result("network_error", type(exc).__name__, retryable=not operation["write"])

    result = map_http_response(response)
    text = json.dumps(result)
    if len(text) > MAX_RESULT_CHARS:
        # The cut text becomes a JSON string value, so the tool message stays valid JSON.
        result = {"ok": result["ok"], "truncated": True, "data": text[:MAX_RESULT_CHARS]}
    return result
