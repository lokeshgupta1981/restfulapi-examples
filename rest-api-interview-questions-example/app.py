"""A small Orders API that answers the common REST interview questions with real HTTP."""
import hashlib
import json
from itertools import count

from fastapi import FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="Orders API")

# Demo tokens: each token maps to the scopes it grants.
TOKENS = {
    "reader-token": {"orders:read"},
    "writer-token": {"orders:read", "orders:write"},
}

orders: dict[int, dict] = {}
# Idempotency-Key value -> the first response (body and headers) for that key.
idempotency_cache: dict[str, dict] = {}
next_id = count(1001)


class OrderIn(BaseModel):
    product: str = Field(min_length=1)
    quantity: int = Field(ge=1)


class OrderPatch(BaseModel):
    product: str | None = Field(default=None, min_length=1)
    quantity: int | None = Field(default=None, ge=1)


def problem(status: int, title: str, detail: str, headers: dict | None = None) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, headers=headers,
                        media_type="application/problem+json")


class ApiError(Exception):
    def __init__(self, status: int, title: str, detail: str, headers: dict | None = None):
        self.status, self.title, self.detail, self.headers = status, title, detail, headers


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return problem(exc.status, exc.title, exc.detail, exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0]
    if first_error["type"] == "json_invalid":
        return problem(400, "Bad Request", "The request body is not valid JSON.")
    field = ".".join(str(part) for part in first_error["loc"][1:])
    return problem(422, "Unprocessable Content", f"{field}: {first_error['msg']}")


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 405:
        # List every method that any route on this path accepts, not only the first route's.
        path = request.url.path
        allowed = sorted({method for route in app.routes
                          if getattr(route, "path_regex", None) and route.path_regex.match(path)
                          for method in route.methods})
        return problem(405, "Method Not Allowed",
                       f"{request.method} is not supported on {path}.",
                       {"Allow": ", ".join(allowed)})
    if exc.status_code == 404:
        return problem(404, "Not Found", "No resource matches this URI.")
    return problem(exc.status_code, "Error", str(exc.detail))


def require_scope(authorization: str | None, scope: str) -> None:
    challenge = {"WWW-Authenticate": 'Bearer realm="orders"'}
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "Unauthorized", "Send a bearer token in the Authorization header.",
                       challenge)
    token = authorization.split(" ", 1)[1].strip()
    if token not in TOKENS:
        raise ApiError(401, "Unauthorized", "The token is not valid.",
                       {"WWW-Authenticate": 'Bearer realm="orders", error="invalid_token"'})
    if scope not in TOKENS[token]:
        raise ApiError(403, "Forbidden", f"The token does not have the scope {scope}.")


def etag_of(order: dict) -> str:
    digest = hashlib.sha256(json.dumps(order, sort_keys=True).encode()).hexdigest()
    return f'"{digest[:16]}"'


def find_order(order_id: int) -> dict:
    if order_id not in orders:
        raise ApiError(404, "Not Found", f"Order {order_id} does not exist.")
    return orders[order_id]


def check_if_match(order: dict, if_match: str | None) -> None:
    if if_match is not None and if_match != etag_of(order):
        raise ApiError(412, "Precondition Failed",
                       "The order changed since you read it. GET it again and retry.")


@app.get("/orders")
def list_orders(authorization: str | None = Header(default=None),
                limit: int = 2, offset: int = 0) -> JSONResponse:
    require_scope(authorization, "orders:read")
    all_orders = list(orders.values())
    page = all_orders[offset:offset + limit]
    headers = {}
    if offset + limit < len(all_orders):
        headers["Link"] = f'</orders?limit={limit}&offset={offset + limit}>; rel="next"'
    return JSONResponse({"items": page, "total": len(all_orders)}, headers=headers)


@app.post("/orders", status_code=201)
def create_order(new_order: OrderIn, response: Response,
                 authorization: str | None = Header(default=None),
                 idempotency_key: str | None = Header(default=None)) -> dict:
    require_scope(authorization, "orders:write")
    if idempotency_key and idempotency_key in idempotency_cache:
        # A retry with a known key gets the first response again; no new order is created.
        saved = idempotency_cache[idempotency_key]
        response.headers.update(saved["headers"])
        return saved["body"]
    order_id = next(next_id)
    order = {"id": order_id, "product": new_order.product,
             "quantity": new_order.quantity, "status": "NEW"}
    orders[order_id] = order
    headers = {"Location": f"/orders/{order_id}", "ETag": etag_of(order)}
    response.headers.update(headers)
    if idempotency_key:
        idempotency_cache[idempotency_key] = {"body": dict(order), "headers": headers}
    return order


@app.get("/orders/{order_id}")
def get_order(order_id: int, authorization: str | None = Header(default=None),
              if_none_match: str | None = Header(default=None)) -> Response:
    require_scope(authorization, "orders:read")
    order = find_order(order_id)
    etag = etag_of(order)
    headers = {"ETag": etag, "Cache-Control": "private, max-age=0, must-revalidate"}
    if if_none_match == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(order, headers=headers)


@app.put("/orders/{order_id}")
def replace_order(order_id: int, new_order: OrderIn,
                  authorization: str | None = Header(default=None),
                  if_match: str | None = Header(default=None)) -> JSONResponse:
    require_scope(authorization, "orders:write")
    order = find_order(order_id)
    check_if_match(order, if_match)
    order.update(product=new_order.product, quantity=new_order.quantity)
    return JSONResponse(order, headers={"ETag": etag_of(order)})


@app.patch("/orders/{order_id}")
def update_order(order_id: int, changes: OrderPatch,
                 authorization: str | None = Header(default=None),
                 if_match: str | None = Header(default=None)) -> JSONResponse:
    require_scope(authorization, "orders:write")
    order = find_order(order_id)
    check_if_match(order, if_match)
    order.update(changes.model_dump(exclude_none=True))
    return JSONResponse(order, headers={"ETag": etag_of(order)})


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int, authorization: str | None = Header(default=None)) -> Response:
    require_scope(authorization, "orders:write")
    find_order(order_id)
    del orders[order_id]
    return Response(status_code=204)
