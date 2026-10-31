"""The same Bookstore API with FastAPI's default error handling, for comparison.

Successful responses look the same as in app.py, but a missing book, an unknown
URL and an invalid body each come back in a different shape. Run it on another
port: uvicorn default_app:app --port 9121
"""
from fastapi import FastAPI, HTTPException

from app import BOOKS, BookIn, to_json

app = FastAPI(title="Bookstore API (default errors)")


@app.get("/books/{book_id}")
def get_book(book_id: str):
    if book_id not in BOOKS:
        raise HTTPException(404, f"There is no book with id {book_id}.")
    return to_json(BOOKS[book_id])


@app.post("/books", status_code=201)
def create_book(body: BookIn):
    return {"received": body.model_dump(mode="json", by_alias=True)}
