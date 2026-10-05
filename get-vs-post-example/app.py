"""Orders API used to compare GET and POST.

Run: uvicorn app:app --port 9120
"""
from collections import Counter

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

app = FastAPI(title="Orders API")

ORDERS = {
    1001: {"id": 1001, "customer_email": "ana@example.com", "status": "paid", "total": 49.0},
    1002: {"id": 1002, "customer_email": "raj@example.com", "status": "pending", "total": 120.0},
    1003: {"id": 1003, "customer_email": "ana@example.com", "status": "shipped", "total": 15.5},
    1004: {"id": 1004, "customer_email": "li@example.com", "status": "paid", "total": 25.0},
}
next_order_id = 1005

# How many requests reached the app, per "METHOD /path".
hits = Counter()
# Every attempt to cancel an order, with or without the session cookie.
cancel_log = []

SESSION_COOKIE = "session"
SESSION_VALUE = "demo-session-1"


@app.middleware("http")
async def count_hits(request: Request, call_next):
    hits[f"{request.method} {request.url.path}"] += 1
    return await call_next(request)


class NewOrder(BaseModel):
    customer_email: str
    total: float


class OrderSearch(BaseModel):
    status: list[str] = []
    customer_email: str | None = None


def find_orders(statuses, customer_email):
    result = []
    for order in ORDERS.values():
        if statuses and order["status"] not in statuses:
            continue
        if customer_email and order["customer_email"] != customer_email:
            continue
        result.append(order)
    return result


@app.get("/orders")
def list_orders(response: Response, status: str | None = None, customer_email: str | None = None):
    statuses = status.split(",") if status else []
    response.headers["Cache-Control"] = "public, max-age=60"
    return {"data": find_orders(statuses, customer_email)}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    if order_id not in ORDERS:
        return Response(status_code=404)
    return ORDERS[order_id]


@app.post("/orders", status_code=201)
def create_order(new_order: NewOrder, response: Response):
    global next_order_id
    order = {"id": next_order_id, "customer_email": new_order.customer_email,
             "status": "pending", "total": new_order.total}
    ORDERS[next_order_id] = order
    next_order_id += 1
    response.headers["Location"] = f"/orders/{order['id']}"
    return order


@app.post("/orders/search")
def search_orders(search: OrderSearch):
    return {"data": find_orders(search.status, search.customer_email)}


@app.get("/stats")
def stats():
    return dict(sorted(hits.items()))


# --- Retry demo: always fails, counts how often the client tried ---------

@app.api_route("/unstable", methods=["GET", "POST"])
def unstable():
    return Response(status_code=503)


# --- CSRF demo -------------------------------------------------------------

@app.get("/login")
def login(response: Response):
    response.set_cookie(SESSION_COOKIE, SESSION_VALUE, httponly=True, samesite="lax")
    return {"logged_in": True}


def cancel(request: Request, order_id: int):
    has_session = request.cookies.get(SESSION_COOKIE) == SESSION_VALUE
    status = 200 if has_session else 401
    cancel_log.append({"method": request.method, "order": order_id,
                       "cookie_sent": has_session, "status": status})
    if not has_session:
        return Response(status_code=status)
    ORDERS[order_id]["status"] = "cancelled"
    return {"id": order_id, "status": "cancelled"}


# Wrong: a state change behind GET.
@app.get("/orders/{order_id}/cancel")
def cancel_with_get(request: Request, order_id: int):
    return cancel(request, order_id)


# Right: the same action behind POST.
@app.post("/orders/{order_id}/cancel")
def cancel_with_post(request: Request, order_id: int):
    return cancel(request, order_id)


@app.get("/cancel-log")
def get_cancel_log():
    return cancel_log
