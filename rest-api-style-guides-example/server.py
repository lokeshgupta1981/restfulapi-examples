"""The same tiny orders API in three styles, mounted side by side.

/azure    follows the Azure REST API Guidelines (Microsoft)
/google   follows Google's AIPs (HTTP/JSON form)
/zalando  follows the Zalando RESTful API Guidelines

Run:  python server.py            (port 8000)
      PORT=29860 python server.py
"""
import base64
import json
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ORDERS = [
    {"id": "ord-1", "customer": "cus-42", "status": "paid", "total": "49.90"},
    {"id": "ord-2", "customer": "cus-42", "status": "pending", "total": "12.00"},
    {"id": "ord-3", "customer": "cus-7", "status": "paid", "total": "80.25"},
]


def make_token(offset: int) -> str:
    # Opaque to the client: a base64url string it must not parse.
    # (AIP-158 asks for more than base64; a real API would encrypt or sign it.)
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode().rstrip("=")


def read_token(token: str) -> int:
    padded = token + "=" * (-len(token) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))["o"]


def page(offset: int, size: int):
    items = ORDERS[offset:offset + size]
    has_more = offset + size < len(ORDERS)
    return items, (make_token(offset + size) if has_more else None)


def find(order_id: str):
    return next((o for o in ORDERS if o["id"] == order_id), None)


# ---------------------------------------------------------------- Azure
azure = FastAPI()
SUPPORTED_API_VERSIONS = {"2026-10-01"}


def azure_order(o):  # camelCase JSON field names
    return {"id": o["id"], "customerId": o["customer"], "status": o["status"], "totalAmount": o["total"]}


def azure_error(status: int, code: str, message: str):
    # Body code and x-ms-error-code header carry the same value.
    return JSONResponse({"error": {"code": code, "message": message}},
                        status_code=status, headers={"x-ms-error-code": code})


def check_api_version(request: Request):
    version = request.query_params.get("api-version")
    if version is None:
        return azure_error(400, "MissingApiVersionParameter",
                           "The api-version query parameter (?api-version=) is required for all requests")
    if version not in SUPPORTED_API_VERSIONS:
        return azure_error(400, "UnsupportedApiVersionValue",
                           f"Unsupported api-version '{version}'. The supported api-versions are '2026-10-01'.")
    return None


@azure.get("/orders")
def azure_list(request: Request, maxpagesize: int = 2, skipToken: str | None = None):
    if (err := check_api_version(request)) is not None:
        return err
    items, token = page(read_token(skipToken) if skipToken else 0, maxpagesize)
    body = {"value": [azure_order(o) for o in items]}
    if token:  # no nextLink at all on the last page
        base = str(request.base_url).rstrip("/")
        body["nextLink"] = f"{base}/azure/orders?api-version=2026-10-01&maxpagesize={maxpagesize}&skipToken={token}"
    return body


@azure.get("/orders/{order_id}")
def azure_get(request: Request, order_id: str):
    if (err := check_api_version(request)) is not None:
        return err
    o = find(order_id)
    if o is None:
        return azure_error(404, "OrderNotFound", f"Order '{order_id}' does not exist.")
    return azure_order(o)


# ---------------------------------------------------------------- Google
google = FastAPI()


def google_order(o):  # proto field customer_id appears in JSON as customerId
    return {"name": f"orders/{o['id']}", "customerId": o["customer"], "status": o["status"].upper(),
            "totalAmount": o["total"]}


@google.get("/v1/orders")
def google_list(pageSize: int = 2, pageToken: str = ""):
    items, token = page(read_token(pageToken) if pageToken else 0, pageSize)
    body = {"orders": [google_order(o) for o in items]}
    if token:  # JSON omits an empty string, so the last page has no nextPageToken
        body["nextPageToken"] = token
    return body


@google.get("/v1/orders/{order_id}")
def google_get(order_id: str):
    o = find(order_id)
    if o is None:
        return JSONResponse(status_code=404, content={"error": {
            "code": 404,
            "message": f"Order 'orders/{order_id}' not found.",
            "status": "NOT_FOUND",
            "details": [{
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "ORDER_NOT_FOUND",
                "domain": "orders.example.com",
                "metadata": {"order": f"orders/{order_id}"},
            }],
        }})
    return google_order(o)


# ---------------------------------------------------------------- Zalando
zalando = FastAPI()


def zalando_order(o):  # snake_case property names
    return {"id": o["id"], "customer_id": o["customer"], "status": o["status"].upper(), "total_amount": o["total"]}


@zalando.get("/orders")
def zalando_list(request: Request, limit: int = 2, cursor: str | None = None):
    offset = read_token(cursor) if cursor else 0
    items, token = page(offset, limit)
    base = str(request.base_url).rstrip("/") + "/zalando/orders"
    body = {"self": f"{base}?limit={limit}" + (f"&cursor={cursor}" if cursor else "")}
    if token:  # no next link on the last page
        body["next"] = f"{base}?limit={limit}&cursor={token}"
    body["items"] = [zalando_order(o) for o in items]
    return body


@zalando.get("/orders/{order_id}")
def zalando_get(order_id: str):
    o = find(order_id)
    if o is None:
        return JSONResponse(status_code=404, media_type="application/problem+json", content={
            "type": "https://example.com/problems/order-not-found",
            "title": "Order not found",
            "status": 404,
            "detail": f"Order '{order_id}' does not exist.",
        })
    return zalando_order(o)


app = FastAPI()
app.mount("/azure", azure)
app.mount("/google", google)
app.mount("/zalando", zalando)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
