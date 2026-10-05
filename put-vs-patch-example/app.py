"""Tickets API that supports PUT (full replacement) and PATCH (partial update).

Run:  uvicorn app:app --port 9110
Set REQUIRE_IF_MATCH=true to reject writes without If-Match (HTTP 428).
"""
import json
import os
from typing import Literal, Optional

import jsonpatch
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

REQUIRE_IF_MATCH = os.environ.get("REQUIRE_IF_MATCH", "false") == "true"
MERGE_PATCH = "application/merge-patch+json"
JSON_PATCH = "application/json-patch+json"
ACCEPT_PATCH = f"{MERGE_PATCH}, {JSON_PATCH}"

app = FastAPI()


class Ticket(BaseModel):
    """The full ticket representation. Only assignee is optional: a body
    without it means "nobody is assigned". Leaving out any other field
    fails validation."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    status: Literal["open", "in_progress", "closed"]
    priority: Literal["low", "normal", "high"]
    assignee: Optional[str] = None
    labels: list[str]


# id -> {"version": int, "data": dict}
tickets = {
    "TCK-1001": {
        "version": 1,
        "data": {
            "title": "Checkout page times out",
            "status": "open",
            "priority": "normal",
            "assignee": "maria",
            "labels": ["checkout"],
        },
    }
}


def etag_of(version: int) -> str:
    return f'"{version}"'


def problem(status: int, title: str, detail: str, headers=None) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, headers=headers,
                        media_type="application/problem+json")


def check_preconditions(request: Request, current):
    """Returns an error response, or None when the write may go ahead."""
    if_match = request.headers.get("if-match")
    if if_match is None:
        if REQUIRE_IF_MATCH and current is not None:
            return problem(428, "Precondition Required",
                           "Send If-Match with the ETag from your last GET.")
        return None
    if current is None:
        return problem(412, "Precondition Failed", "The ticket does not exist.")
    tags = [t.strip() for t in if_match.split(",")]
    if "*" in tags or etag_of(current["version"]) in tags:
        return None
    return problem(412, "Precondition Failed",
                   f"The ticket changed. Current ETag is {etag_of(current['version'])}.",
                   headers={"ETag": etag_of(current["version"])})


def validate(data: dict):
    """Returns (clean_data, None) or (None, error_response)."""
    try:
        return Ticket.model_validate(data).model_dump(), None
    except ValidationError as err:
        errors = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                  for e in err.errors()]
        response = problem(422, "Unprocessable Content", "The ticket is not valid.")
        body = json.loads(response.body)
        body["errors"] = errors
        return None, JSONResponse(body, status_code=422,
                                  media_type="application/problem+json")


def save(ticket_id: str, data: dict) -> int:
    """Stores the data. The version only changes when the data changes."""
    current = tickets.get(ticket_id)
    if current is not None and current["data"] == data:
        return current["version"]
    version = 1 if current is None else current["version"] + 1
    tickets[ticket_id] = {"version": version, "data": data}
    return version


def merge_patch(target, patch):
    """JSON Merge Patch, RFC 7396 section 2."""
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for name, value in patch.items():
        if value is None:
            result.pop(name, None)
        else:
            result[name] = merge_patch(result.get(name), value)
    return result


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    current = tickets.get(ticket_id)
    if current is None:
        return problem(404, "Not Found", f"No ticket {ticket_id}.")
    return JSONResponse(current["data"], headers={"ETag": etag_of(current["version"])})


@app.options("/tickets/{ticket_id}")
def ticket_options(ticket_id: str):
    return Response(status_code=204, headers={
        "Allow": "GET, PUT, PATCH, OPTIONS", "Accept-Patch": ACCEPT_PATCH})


@app.put("/tickets/{ticket_id}")
async def put_ticket(ticket_id: str, request: Request):
    current = tickets.get(ticket_id)
    error = check_preconditions(request, current)
    if error:
        return error
    try:
        body = await request.json()
    except ValueError:
        return problem(400, "Bad Request", "The body is not valid JSON.")
    if not isinstance(body, dict):
        return problem(400, "Bad Request", "The body must be a JSON object.")
    data, error = validate(body)
    if error:
        return error
    version = save(ticket_id, data)
    # RFC 9110, section 9.3.4: send the new ETag only when the stored ticket
    # is identical to the body the client sent. When the server filled in a
    # field (here: a missing assignee), the client's copy is not current.
    headers = {"ETag": etag_of(version)} if data == body else {}
    if current is None:
        headers["Location"] = f"/tickets/{ticket_id}"
        return JSONResponse(data, status_code=201, headers=headers)
    return JSONResponse(data, status_code=200, headers=headers)


@app.patch("/tickets/{ticket_id}")
async def patch_ticket(ticket_id: str, request: Request):
    content_type = request.headers.get("content-type", "").split(";")[0].strip()
    if content_type not in (MERGE_PATCH, JSON_PATCH):
        return problem(415, "Unsupported Media Type",
                       f"Send the patch as {MERGE_PATCH} or {JSON_PATCH}.",
                       headers={"Accept-Patch": ACCEPT_PATCH})
    current = tickets.get(ticket_id)
    if current is None:
        return problem(404, "Not Found", f"No ticket {ticket_id}.")
    error = check_preconditions(request, current)
    if error:
        return error
    try:
        patch = await request.json()
    except ValueError:
        return problem(400, "Bad Request", "The patch document is not valid JSON.")

    if content_type == MERGE_PATCH:
        if not isinstance(patch, dict):
            return problem(400, "Bad Request", "A merge patch must be a JSON object.")
        patched = merge_patch(current["data"], patch)
    else:
        try:
            patched = jsonpatch.apply_patch(current["data"], patch)
        except jsonpatch.InvalidJsonPatch as err:
            return problem(400, "Bad Request", f"The JSON Patch is not valid: {err}")
        except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as err:
            return problem(409, "Conflict", f"The patch cannot be applied: {err}")
        except (TypeError, AttributeError):
            return problem(400, "Bad Request", "A JSON Patch must be an array of operations.")

    # Validate the result, not the patch. Nothing is stored if it fails.
    data, error = validate(patched)
    if error:
        return error
    version = save(ticket_id, data)
    return JSONResponse(data, headers={"ETag": etag_of(version)})
