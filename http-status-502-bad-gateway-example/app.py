"""A small orders API that can fail on purpose, so nginx returns HTTP 502."""
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Orders API")

ORDERS = {
    "1001": {"id": "1001", "status": "SHIPPED", "total": "49.90", "currency": "EUR"},
    "1002": {"id": "1002", "status": "PENDING", "total": "15.00", "currency": "EUR"},
}


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = ORDERS.get(order_id)
    if order is None:
        return JSONResponse(
            status_code=404,
            media_type="application/problem+json",
            content={"title": "Not Found", "status": 404, "detail": f"Order {order_id} does not exist."},
        )
    return order


@app.get("/fail/crash-before-response")
def crash_before_response():
    # The worker process dies before it writes a single byte of the response.
    os._exit(1)


@app.get("/fail/crash-mid-body")
def crash_mid_body():
    # The status line and headers go out, then the process dies halfway through the body.
    def body():
        yield b'{"orders": [' + b'{"id": "1001"},' * 200
        os._exit(1)

    return StreamingResponse(body(), media_type="application/json")


@app.get("/fail/huge-header")
def huge_header():
    # A 16 KB response header is larger than nginx's default proxy_buffer_size (4k or 8k).
    trace = "x" * 16_000
    return JSONResponse({"id": "1001"}, headers={"X-Debug-Trace": trace})


@app.post("/fail/reset")
def reset():
    # The process exits without reading the request body. The kernel answers the
    # unread bytes with a TCP RST, so nginx sees "Connection reset by peer".
    os._exit(1)
