"""The remote inventory API that the bookstore depends on (port 9601).

POST /admin/mode?mode=healthy|slow|down switches its behaviour:
  healthy: answers at once
  slow:    waits 5 seconds before answering (like an overloaded database)
  down:    answers HTTP 503 at once
GET /admin/stats shows how many stock requests it has received.
"""
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()
STOCK = {1: 7, 2: 0, 3: 12}
state = {"mode": "healthy", "requests": 0}


@app.get("/stock/{book_id}")
async def stock(book_id: int):
    state["requests"] += 1
    if state["mode"] == "slow":
        await asyncio.sleep(5)
    if state["mode"] == "down":
        return JSONResponse({"detail": "inventory database unavailable"}, status_code=503)
    if book_id not in STOCK:
        raise HTTPException(404, "unknown book")
    return {"book_id": book_id, "in_stock": STOCK[book_id]}


@app.post("/admin/mode")
async def set_mode(mode: str):
    state["mode"] = mode
    return state


@app.get("/admin/stats")
async def stats():
    return state


@app.post("/admin/reset")
async def reset():
    state["requests"] = 0
    return state
