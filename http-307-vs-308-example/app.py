"""Orders API used to compare HTTP 301, 302, 303, 307 and 308 redirects."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

app = FastAPI()

ORDERS = []


@app.post("/v1/orders")
async def create_order_v1():
    # The v1 endpoint moved for good: 308 keeps POST and the JSON body.
    # A short max-age limits how long browsers cache the redirect.
    return RedirectResponse(url="/v2/orders", status_code=308,
                            headers={"Cache-Control": "max-age=3600"})


@app.post("/v2/orders", status_code=201)
async def create_order_v2(request: Request):
    order = await request.json()
    order["id"] = 1000 + len(ORDERS) + 1
    ORDERS.append(order)
    return JSONResponse(order, status_code=201,
                        headers={"Location": f"/v2/orders/{order['id']}"})


@app.api_route("/lab/{code}", methods=["GET", "POST", "PUT", "DELETE"])
async def lab_redirect(code: int, request: Request):
    # Redirect to /echo on the same host, or to another host with ?cross=1.
    target = "/echo"
    if request.query_params.get("cross") == "1":
        target = "http://localhost:9190/echo"
    return RedirectResponse(url=target, status_code=code)


@app.api_route("/echo", methods=["GET", "POST", "PUT", "DELETE"])
async def echo(request: Request):
    # Report what arrived after the redirect: method, body size, Authorization.
    body = await request.body()
    auth = "kept" if request.headers.get("authorization") else "dropped"
    summary = f"{request.method:4} body={len(body)} bytes  Authorization {auth}"
    return JSONResponse({"summary": summary, "body": body.decode()})


@app.post("/orders")
async def create_order(request: Request):
    # Called as POST /orders/ (trailing slash), Starlette answers 307 first.
    return await create_order_v2(request)


@app.get("/loop/{hop}")
async def loop(hop: int):
    # Never-ending chain of 307 redirects, to see where each client stops.
    return RedirectResponse(url=f"/loop/{hop + 1}", status_code=307)


HITS = {"307": 0, "308": 0, "308 + Cache-Control: no-store": 0}


@app.get("/cache/{code}")
async def cache_check(code: int, cc: str | None = None):
    # Without Cache-Control the browser decides whether to store the redirect.
    key = str(code) if cc is None else f"{code} + Cache-Control: {cc}"
    HITS[key] += 1
    headers = {"Cache-Control": cc} if cc else None
    return RedirectResponse(url="/echo", status_code=code, headers=headers)


@app.get("/hits")
async def hits():
    return HITS
