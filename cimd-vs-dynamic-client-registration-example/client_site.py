"""The client's own website. It hosts the Client ID Metadata Document.

The URL of /oauth/client-metadata.json IS the client_id.
The other documents are broken on purpose, to show what the
authorization server rejects.
"""

import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

PORT = int(os.environ.get("CLIENT_SITE_PORT", "8443"))
BASE = os.environ.get("CLIENT_SITE_BASE", f"https://localhost:{PORT}")
CALLBACK = os.environ.get("CLIENT_CALLBACK", "http://127.0.0.1:8765/callback")

app = FastAPI()


def document(path: str, **overrides) -> dict:
    doc = {
        "client_id": f"{BASE}{path}",
        "client_name": "Orders Desktop",
        "client_uri": BASE,
        "redirect_uris": [CALLBACK],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    doc.update(overrides)
    return doc


@app.get("/oauth/client-metadata.json")
def client_metadata():
    return JSONResponse(document("/oauth/client-metadata.json"),
                        headers={"Cache-Control": "max-age=3600"})


# ---- broken documents for the demo

@app.get("/oauth/copied.json")
def copied():
    """Someone copied our document to another URL without changing client_id."""
    return document("/oauth/client-metadata.json")


@app.get("/oauth/with-secret.json")
def with_secret():
    return document("/oauth/with-secret.json", client_secret="fake-demo-secret",
                    token_endpoint_auth_method="client_secret_basic")


@app.get("/oauth/moved.json")
def moved():
    return RedirectResponse(f"{BASE}/oauth/client-metadata.json", status_code=301)


@app.get("/oauth/huge.json")
def huge():
    return document("/oauth/huge.json", client_name="Orders Desktop " + "x" * 6000)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning",
                ssl_certfile="certs/localhost.pem", ssl_keyfile="certs/localhost-key.pem")
