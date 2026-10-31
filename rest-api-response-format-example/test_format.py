"""Contract tests: every endpoint of app.py follows the same response format.

Run with: pytest -v
"""
import re

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

NEW_BOOK = {"title": "REST in Practice", "author": "Jim Webber", "isbn": "9780596805821",
            "price": {"amount": "34.99", "currency": "USD"}, "publishedOn": "2010-09-01"}

CAMEL = re.compile(r"^[a-z][a-zA-Z0-9]*$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys(v)


def assert_book(book):
    assert isinstance(book["id"], str)
    assert TIMESTAMP.match(book["createdAt"])
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", book["publishedOn"])
    assert isinstance(book["price"]["amount"], str)
    assert "subtitle" in book                      # present, even when it is null


@pytest.mark.parametrize("method, path, body, status", [
    ("GET", "/books/9999", None, 404),
    ("GET", "/no-such-url", None, 404),
    ("PUT", "/books/1001", None, 405),
    ("GET", "/books?limit=0", None, 422),
    ("GET", "/books?cursor=@@@", None, 400),
    ("POST", "/books", {"title": ""}, 422),
    ("DELETE", "/books/9999", None, 404),
])
def test_every_error_is_problem_details(method, path, body, status):
    r = client.request(method, path, json=body)
    assert r.status_code == status
    assert r.headers["content-type"] == "application/problem+json"
    problem = r.json()
    assert problem["status"] == status
    assert problem["type"].startswith("https://")
    assert problem["title"] and problem["detail"]


def test_unexpected_crash_is_problem_details_without_internals():
    @app.get("/crash-for-test")
    def crash():
        raise RuntimeError("database password is hunter2")

    r = TestClient(app, raise_server_exceptions=False).get("/crash-for-test")
    assert r.status_code == 500
    assert r.headers["content-type"] == "application/problem+json"
    assert "hunter2" not in r.text and "RuntimeError" not in r.text


def test_validation_errors_point_at_fields():
    r = client.post("/books", json={**NEW_BOOK, "price": {"amount": "-1", "currency": "USD"}})
    assert r.json()["errors"] == [{"pointer": "/price/amount",
                                   "detail": "Input should be greater than 0"}]


def test_single_book_is_the_plain_object():
    r = client.get("/books/1001")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    book = r.json()
    assert "data" not in book and "success" not in book
    assert_book(book)
    assert all(CAMEL.match(k) for k in keys(book))


def test_list_is_an_object_with_items_and_next():
    first = client.get("/books?limit=2").json()
    assert set(first) == {"items", "next"}
    assert len(first["items"]) == 2
    for book in first["items"]:
        assert_book(book)
    second = client.get(first["next"]).json()
    assert second["items"][0]["id"] == "1003"


def test_last_page_has_null_next_and_empty_result_is_200():
    r = client.get("/books?author=Nobody")
    assert r.status_code == 200
    assert r.json() == {"items": [], "next": None}


def test_create_returns_201_location_and_the_new_book():
    r = client.post("/books", json=NEW_BOOK)
    assert r.status_code == 201
    created = r.json()
    assert_book(created)
    assert r.headers["location"] == f"/books/{created['id']}"
    assert client.get(r.headers["location"]).json() == created


def test_delete_returns_204_without_a_body():
    created = client.post("/books", json=NEW_BOOK).json()
    r = client.delete(f"/books/{created['id']}")
    assert r.status_code == 204
    assert r.content == b""
