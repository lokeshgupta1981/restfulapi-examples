"""Plain-HTTP listener that sends every request to the HTTPS port with 308."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

app = FastAPI()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def to_https(path: str, request: Request):
    target = request.url.replace(scheme="https", port=9192)
    return RedirectResponse(url=str(target), status_code=308)
