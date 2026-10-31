"""A client for the Bookstore API (app.py on port 9120). Uses the requests library."""
import os

import requests

BASE = os.environ.get("BASE", "http://localhost:9120")


# --- 1. The "200 for everything" envelope hides the failure from requests ---

def book_title_envelope(book_id):
    r = requests.get(f"{BASE}/envelope/books/{book_id}")
    r.raise_for_status()                 # status is 200, so nothing is raised
    return r.json()["data"]["title"]


# --- 2. With status codes and Problem Details, one helper handles every error ---

class ApiError(Exception):
    def __init__(self, response):
        problem = response.json()
        self.status = problem["status"]
        self.type = problem["type"]
        self.errors = problem.get("errors", [])
        super().__init__(f'{problem["status"]} {problem["title"]}: {problem["detail"]}')


def call(method, path, **kwargs):
    r = requests.request(method, BASE + path, **kwargs)
    if r.headers.get("Content-Type", "").startswith("application/problem+json"):
        raise ApiError(r)
    r.raise_for_status()                 # anything else that is not 2xx
    return r


def book_title(book_id):
    return call("GET", f"/books/{book_id}").json()["title"]


def all_titles(limit=2):
    """Follow the next link until it is null."""
    titles, url, pages = [], f"/books?limit={limit}", 0
    while url:
        page = call("GET", url.removeprefix(BASE)).json()
        titles += [b["title"] for b in page["items"]]
        url, pages = page["next"], pages + 1
    return titles, pages


if __name__ == "__main__":
    print("Envelope, existing book:", book_title_envelope("1001"))
    try:
        book_title_envelope("9999")
    except Exception as e:
        print("Envelope, missing book:", type(e).__name__ + ":", e)

    print("Status codes, existing book:", book_title("1001"))
    try:
        book_title("9999")
    except ApiError as e:
        print("Status codes, missing book: ApiError:", e)

    try:
        call("POST", "/books", json={"title": "API Design Patterns", "author": "JJ Geewax",
                                     "isbn": "9781617295850",
                                     "price": {"amount": "59.99", "currency": "usd"}})
    except ApiError as e:
        print("Create with bad body: ApiError:", e)
        for err in e.errors:
            print("   ", err["pointer"], "->", err["detail"])

    titles, pages = all_titles()
    print(f"All titles ({pages} pages):", titles)
