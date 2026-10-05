"""Order tracking server with three push endpoints for the same event log:

  GET  /orders/{order_id}/updates?after=N    long polling (JSON)
  GET  /orders/{order_id}/stream             server-sent events (text/event-stream)
  WS   /orders/{order_id}/socket?after=N     WebSocket (JSON text frames)

  POST /orders/{order_id}/events             publish a status event
  POST /admin/drop-connections               close every open stream and socket
                                             (simulates a deploy or a network drop)
"""

import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Header, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

LONG_POLL_WAIT = float(os.getenv("LONG_POLL_WAIT", "25"))   # seconds
HEARTBEAT = float(os.getenv("HEARTBEAT", "15"))             # seconds
SSE_RETRY_MS = 3000
SSE_NO_BUFFER_HEADER = os.getenv("SSE_NO_BUFFER_HEADER", "1") == "1"

app = FastAPI()


class EventLog:
    """In-memory event log per order. Event ids grow by one, so a client
    can say "give me everything after id N"."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.changed = asyncio.Condition()
        self.generation = 0   # bumped by drop-connections

    def after(self, order_id: str, last_id: int) -> list[dict]:
        return [e for e in self.events if e["order_id"] == order_id and e["id"] > last_id]

    async def publish(self, order_id: str, status: str) -> dict:
        async with self.changed:
            event = {
                "id": len(self.events) + 1,
                "order_id": order_id,
                "status": status,
                "sent_at": round(time.time(), 3),
            }
            self.events.append(event)
            self.changed.notify_all()
            return event

    async def drop_all(self) -> None:
        async with self.changed:
            self.generation += 1
            self.changed.notify_all()

    def version(self) -> tuple[int, int]:
        return len(self.events), self.generation

    async def wait(self, seen: tuple[int, int], timeout: float) -> None:
        """Wait until the log changes after the version `seen`, or the timeout."""
        async with self.changed:
            if self.version() != seen:
                return
            try:
                await asyncio.wait_for(self.changed.wait(), timeout)
            except TimeoutError:
                pass


log = EventLog()


class NewEvent(BaseModel):
    status: str


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(Path(__file__).with_name("index.html"))


@app.post("/orders/{order_id}/events", status_code=201)
async def publish(order_id: str, body: NewEvent) -> dict:
    return await log.publish(order_id, body.status)


@app.post("/admin/drop-connections", status_code=204)
async def drop_connections() -> Response:
    await log.drop_all()
    return Response(status_code=204)


# 1. Long polling ---------------------------------------------------------
@app.get("/orders/{order_id}/updates")
async def long_poll(order_id: str, after: int = Query(0, ge=0)) -> JSONResponse:
    deadline = time.monotonic() + LONG_POLL_WAIT
    while True:
        seen = log.version()
        events = log.after(order_id, after)
        remaining = deadline - time.monotonic()
        if events or remaining <= 0:
            break
        await log.wait(seen, remaining)
    last_id = events[-1]["id"] if events else after
    return JSONResponse(
        {"events": events, "last_id": last_id},
        headers={"Cache-Control": "no-store"},
    )


# 2. Server-sent events ---------------------------------------------------
def sse_message(event: dict) -> str:
    return f"id: {event['id']}\nevent: status\ndata: {json.dumps(event)}\n\n"


@app.get("/orders/{order_id}/stream")
async def stream(
    request: Request,
    order_id: str,
    last_event_id: str | None = Header(None),
    after: int = Query(0, ge=0),
) -> StreamingResponse:
    start = int(last_event_id) if last_event_id and last_event_id.isdigit() else after
    print(f"SSE connect order={order_id} Last-Event-ID={last_event_id} start_after={start}", flush=True)

    async def body():
        generation = log.generation
        last = start
        yield f"retry: {SSE_RETRY_MS}\n\n"
        while True:
            seen = log.version()
            for event in log.after(order_id, last):
                last = event["id"]
                yield sse_message(event)
            if await request.is_disconnected() or log.generation != generation:
                return
            await log.wait(seen, HEARTBEAT)
            if log.version() == seen:
                yield ": ping\n\n"   # comment line keeps proxies from closing an idle stream

    headers = {"Cache-Control": "no-store"}
    if SSE_NO_BUFFER_HEADER:
        headers["X-Accel-Buffering"] = "no"
    return StreamingResponse(body(), media_type="text/event-stream", headers=headers)


# 3. WebSocket ------------------------------------------------------------
@app.websocket("/orders/{order_id}/socket")
async def socket(websocket: WebSocket, order_id: str, after: int = 0) -> None:
    await websocket.accept()
    generation = log.generation
    last = after

    async def push() -> None:
        nonlocal last
        while log.generation == generation:
            seen = log.version()
            for event in log.after(order_id, last):
                last = event["id"]
                await websocket.send_text(json.dumps(event))
            await log.wait(seen, HEARTBEAT)
        await websocket.close(code=1012)   # 1012 = service restart

    async def receive() -> None:
        while True:
            message = json.loads(await websocket.receive_text())
            if message.get("action") == "cancel":
                await log.publish(order_id, "cancel_requested")

    tasks = [asyncio.create_task(push()), asyncio.create_task(receive())]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        error = task.exception()
        if error and not isinstance(error, WebSocketDisconnect):
            raise error   # a client that disconnects is normal, anything else is a bug
