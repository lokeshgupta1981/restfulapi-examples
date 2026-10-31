"""A minimal API gateway for the bookstore, written for learning.

One entry point in front of the books and orders services. For every request it:
  1. gives the request an ID,
  2. checks the API key (authentication),
  3. applies a rate limit per client,
  4. answers GET /api/books from a short cache when it can,
  5. routes the request to the right service, with a timeout,
  6. writes one access-log line.
It also has one composed endpoint, /api/order-summary/{id}, that calls both services.

Do not use this in production; use a real gateway (see the article).
"""
import os
import time
import uuid

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

BOOKS_URL = os.environ.get("BOOKS_URL", "http://127.0.0.1:8001")
ORDERS_URL = os.environ.get("ORDERS_URL", "http://127.0.0.1:8002")

# Route table: public path prefix -> (service base URL, path prefix on the service)
ROUTES = {
    "/api/books": (BOOKS_URL, "/books"),
    "/api/orders": (ORDERS_URL, "/orders"),
}

# DEMO KEYS ONLY. Real keys live in a secret store, never in code.
API_KEYS = {
    "demo-key-mobile-123": {"client": "mobile-app", "limit": 5},
    "demo-key-partner-456": {"client": "partner-shop", "limit": 100},
}
# bench.sh raises the partner limit so the benchmark is not rate limited
API_KEYS["demo-key-partner-456"]["limit"] = int(os.environ.get("PARTNER_LIMIT", "100"))
WINDOW_SECONDS = 10       # rate-limit window
CACHE_TTL_SECONDS = 30    # how long GET /api/books stays cached
UPSTREAM_TIMEOUT = 2.0    # seconds to wait for a service

app = FastAPI(title="bookstore gateway")
client = httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT)
windows = {}   # client -> (window start, count)
cache = {}     # path -> (expires at, status, body, content type)


def problem(status, title, request_id, headers=None):
    """Error in RFC 9457 Problem Details format."""
    body = {"type": "about:blank", "title": title, "status": status}
    h = {"X-Request-Id": request_id} | (headers or {})
    return JSONResponse(body, status, headers=h, media_type="application/problem+json")


def check_rate_limit(client_id, limit):
    """Fixed window: at most `limit` requests per WINDOW_SECONDS per client."""
    now = time.monotonic()
    start, count = windows.get(client_id, (now, 0))
    if now - start >= WINDOW_SECONDS:
        start, count = now, 0
    count += 1
    windows[client_id] = (start, count)
    remaining = max(limit - count, 0)
    retry_after = max(1, round(WINDOW_SECONDS - (now - start)))
    return count <= limit, remaining, retry_after


def find_route(path):
    for prefix, (base, target) in ROUTES.items():
        if path == prefix or path.startswith(prefix + "/"):
            return base + target + path[len(prefix):]
    return None


@app.middleware("http")
async def access_log(request: Request, call_next):
    started = time.perf_counter()
    request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    response = await call_next(request)
    ms = (time.perf_counter() - started) * 1000
    print(f"gateway id={request.state.request_id} client={getattr(request.state, 'client', '-')} "
          f"{request.method} {request.url.path} -> {response.status_code} "
          f"cache={response.headers.get('x-cache', '-')} {ms:.1f}ms", flush=True)
    return response


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def gateway(request: Request, rest: str):
    rid = request.state.request_id

    # 1. Authentication: who is calling?
    key = request.headers.get("x-api-key")
    if key not in API_KEYS:
        return problem(401, "missing or invalid API key", rid, {"WWW-Authenticate": "ApiKey"})
    caller = API_KEYS[key]
    request.state.client = caller["client"]

    # 2. Rate limiting per client
    allowed, remaining, retry_after = check_rate_limit(caller["client"], caller["limit"])
    limit_headers = {"X-RateLimit-Limit": str(caller["limit"]),
                     "X-RateLimit-Remaining": str(remaining)}
    if not allowed:
        return problem(429, "rate limit exceeded", rid, limit_headers | {"Retry-After": str(retry_after)})

    path = request.url.path
    if path.startswith("/api/order-summary/"):
        return await order_summary(path.rsplit("/", 1)[-1], caller, rid, limit_headers)

    # 3. Cache: answer repeated GETs of the book list without calling the service
    if request.method == "GET" and path == "/api/books":
        hit = cache.get(path)
        if hit and hit[0] > time.monotonic():
            _, status, body, ctype = hit
            return Response(body, status, media_type=ctype,
                            headers=limit_headers | {"X-Request-Id": rid, "X-Cache": "HIT"})

    # 4. Routing
    target = find_route(path)
    if target is None:
        return problem(404, "no route for this path", rid, limit_headers)

    headers = {k: v for k, v in request.headers.items()
               if k not in ("host", "x-api-key", "content-length")}
    headers |= {"X-Request-Id": rid, "X-Client-Id": caller["client"],
                "Forwarded": f'for="{request.client.host}";proto={request.url.scheme}'}
    try:
        upstream = await client.request(request.method, target, params=request.query_params,
                                        headers=headers, content=await request.body())
    except httpx.TimeoutException:
        return problem(504, "upstream service timed out", rid, limit_headers)
    except httpx.TransportError:
        return problem(502, "upstream service unreachable", rid, limit_headers)

    out_headers = limit_headers | {"X-Request-Id": rid}
    ctype = upstream.headers.get("content-type", "application/json")
    if request.method == "GET" and path == "/api/books" and upstream.status_code == 200:
        cache[path] = (time.monotonic() + CACHE_TTL_SECONDS, 200, upstream.content, ctype)
        out_headers["X-Cache"] = "MISS"
    return Response(upstream.content, upstream.status_code, media_type=ctype, headers=out_headers)


async def order_summary(order_id, caller, rid, limit_headers):
    """Composition: one client call, two service calls."""
    h = {"X-Request-Id": rid, "X-Client-Id": caller["client"]}
    try:
        order = await client.get(f"{ORDERS_URL}/orders/{order_id}", headers=h)
        if order.status_code != 200:
            return Response(order.content, order.status_code, media_type="application/json",
                            headers=limit_headers | {"X-Request-Id": rid})
        o = order.json()
        book = (await client.get(f"{BOOKS_URL}/books/{o['bookId']}", headers=h)).json()
    except httpx.TimeoutException:
        return problem(504, "upstream service timed out", rid, limit_headers)
    except httpx.TransportError:
        return problem(502, "upstream service unreachable", rid, limit_headers)
    summary = {"orderId": o["id"], "quantity": o["quantity"], "book": book["title"],
               "total": round(book["price"] * o["quantity"], 2)}
    return JSONResponse(summary, headers=limit_headers | {"X-Request-Id": rid})
