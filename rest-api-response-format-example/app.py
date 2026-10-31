"""Bookstore API that uses one response format for every endpoint.

- A single resource is returned as the plain JSON object.
- A collection is an object: {"items": [...], "next": <url or null>}.
- Errors use Problem Details (RFC 9457) with Content-Type application/problem+json.
- Success or failure is carried by the HTTP status code.

/envelope/books/{id} shows the "success/data/error with 200 for everything"
format for comparison. Do not copy that one.
"""
import base64
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

app = FastAPI(title="Bookstore API")

PROBLEM = "application/problem+json"
PROBLEM_BASE = "https://api.example.com/problems/"


# ---------- models: camelCase on the wire, snake_case in Python ----------

class Wire(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Money(Wire):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class BookIn(Wire):
    title: str = Field(min_length=1, max_length=200)
    subtitle: str | None = None
    author: str = Field(min_length=1)
    isbn: str = Field(pattern=r"^97[89]\d{10}$")
    price: Money
    published_on: date


class Book(BookIn):
    id: str
    created_at: datetime


def to_json(book: Book) -> dict:
    data = book.model_dump(mode="json", by_alias=True)
    data["createdAt"] = book.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": data.pop("id"), **data}


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


BOOKS: dict[str, Book] = {}
for i, (title, subtitle, author, isbn, amount, published, created) in enumerate([
    ("RESTful Web APIs", None, "Leonard Richardson", "9781449358068", "39.99", "2013-09-01", "2026-10-01T08:30:00"),
    ("Designing Web APIs", "Building APIs That Developers Love", "Brenda Jin", "9781492026921", "44.99", "2018-09-01", "2026-10-02T09:00:00"),
    ("API Design Patterns", None, "JJ Geewax", "9781617295850", "59.99", "2021-07-01", "2026-10-03T10:15:00"),
    ("The Design of Web APIs", None, "Arnaud Lauret", "9781617295102", "49.99", "2019-10-01", "2026-10-04T11:45:00"),
    ("Building Microservices", "Designing Fine-Grained Systems", "Sam Newman", "9781492034025", "54.99", "2021-08-01", "2026-10-05T12:00:00"),
], start=1001):
    BOOKS[str(i)] = Book(id=str(i), title=title, subtitle=subtitle, author=author, isbn=isbn,
                         price=Money(amount=Decimal(amount), currency="USD"),
                         published_on=date.fromisoformat(published), created_at=utc(created))
NEXT_ID = 1006


# ---------- errors: one Problem Details format ----------

def problem(status: int, slug: str, title: str, detail: str, request: Request,
            headers: dict | None = None, **extra) -> JSONResponse:
    body = {"type": PROBLEM_BASE + slug, "title": title, "status": status,
            "detail": detail, "instance": request.url.path, **extra}
    return JSONResponse(body, status_code=status, media_type=PROBLEM, headers=headers)


class NotFound(Exception):
    def __init__(self, detail: str):
        self.detail = detail


@app.exception_handler(NotFound)
async def not_found(request: Request, exc: NotFound):
    return problem(404, "not-found", "Resource not found", exc.detail, request)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    # Unknown URLs and wrong methods also get Problem Details, not {"detail": "Not Found"}.
    if exc.status_code == 404:
        return problem(404, "not-found", "Resource not found",
                       f"Nothing is served at {request.url.path}.", request)
    if exc.status_code == 405:
        allowed = sorted({m for r in app.routes if isinstance(r, APIRoute)
                          and r.matches(request.scope)[0] != Match.NONE for m in r.methods})
        return problem(405, "method-not-allowed", "Method not allowed",
                       f"{request.method} is not supported here.", request,
                       headers={"Allow": ", ".join(allowed)})
    return problem(exc.status_code, "http-error", "HTTP error", str(exc.detail), request,
                   headers=exc.headers)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Log the details on the server; never send a stack trace to the client.
    return problem(500, "internal-error", "Internal server error",
                   "Something went wrong on our side. Please try again later.", request)


def pointer(loc) -> str:
    # ("body", "price", "amount") -> "/price/amount"; ("query", "limit") -> "limit"
    if loc and loc[0] == "body":
        parts = [to_camel(p) if isinstance(p, str) else str(p) for p in loc[1:]]
        return "/" + "/".join(parts)
    return str(loc[-1])


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errs = exc.errors()
    if any(e["type"] == "json_invalid" for e in errs):
        return problem(400, "malformed-json", "Malformed JSON",
                       "The request body is not valid JSON.", request)
    items = []
    for e in errs:
        key = "pointer" if e["loc"] and e["loc"][0] == "body" else "parameter"
        items.append({key: pointer(e["loc"]), "detail": e["msg"]})
    return problem(422, "validation-error", "Your request is not valid",
                   f"{len(items)} field(s) failed validation.", request, errors=items)


# ---------- endpoints ----------

def encode_cursor(book_id: str) -> str:
    return base64.urlsafe_b64encode(book_id.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> str:
    book_id = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
    if not book_id.isdigit():
        raise ValueError("not a cursor")
    return book_id


@app.get("/books")
def list_books(request: Request, limit: int = Query(10, ge=1, le=50), cursor: str | None = None,
               author: str | None = None):
    ids = sorted(BOOKS)
    if author:
        ids = [i for i in ids if BOOKS[i].author.lower() == author.lower()]
    if cursor:
        try:
            after = decode_cursor(cursor)
        except ValueError:
            return problem(400, "invalid-cursor", "Invalid cursor",
                           "Use the next link from the previous page.", request)
        ids = [i for i in ids if i > after]
    page = ids[:limit]
    nxt = None
    if len(ids) > limit:
        nxt = str(request.url.include_query_params(cursor=encode_cursor(page[-1])))
    return {"items": [to_json(BOOKS[i]) for i in page], "next": nxt}


@app.get("/books/{book_id}")
def get_book(book_id: str):
    if book_id not in BOOKS:
        raise NotFound(f"There is no book with id {book_id}.")
    return to_json(BOOKS[book_id])


@app.post("/books", status_code=201)
def create_book(body: BookIn, response: Response):
    global NEXT_ID
    book = Book(id=str(NEXT_ID), created_at=datetime.now(timezone.utc).replace(microsecond=0),
                **body.model_dump())
    BOOKS[book.id] = book
    NEXT_ID += 1
    response.headers["Location"] = f"/books/{book.id}"
    return to_json(book)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: str):
    if BOOKS.pop(book_id, None) is None:
        raise NotFound(f"There is no book with id {book_id}.")
    return Response(status_code=204)


# ---------- for comparison only: the "200 for everything" envelope ----------

@app.get("/envelope/books/{book_id}")
def get_book_envelope(book_id: str):
    if book_id not in BOOKS:
        return {"success": False, "data": None,
                "error": {"code": "NOT_FOUND", "message": f"There is no book with id {book_id}."}}
    return {"success": True, "data": to_json(BOOKS[book_id]), "error": None}
