"""The same document route in FastAPI, to see what a framework decodes for us.

Run: uvicorn fastapi_app:app --port 9161
"""
import json

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse


class AsciiJSONResponse(JSONResponse):
    """JSON with non-ASCII characters written as \\uXXXX, so we can see them in curl."""

    def render(self, content) -> bytes:
        return json.dumps(content).encode("ascii")


app = FastAPI(default_response_class=AsciiJSONResponse)


@app.get("/docs/{name}")
def get_doc(name: str, request: Request, tag: list[str] = Query(default=[])):
    # FastAPI hands us values that are already decoded. Never decode them again.
    return {"raw_path": request.scope["raw_path"].decode("ascii"),
            "name": name,
            "tag": tag}


@app.get("/files/{name:path}")
def get_file(name: str, request: Request):
    # The ":path" converter accepts slashes, so AB%2F12 and AB/12 look the same here.
    return {"raw_path": request.scope["raw_path"].decode("ascii"), "name": name}
