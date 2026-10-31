"""A client pages through orders while a new order is created.

10 orders exist, the page size is 3. The client reads page 1, then a new order
arrives, then the client reads the remaining pages. Does the client see it?
"""
from ids import KINDS, new_id
from store import OrderStore

TRIALS, EXISTING, PAGE = 1000, 10, 3

for kind in KINDS:
    missed = 0
    for _ in range(TRIALS):
        store = OrderStore()
        for n in range(EXISTING):
            store.insert(new_id(kind), {"item": f"book-{n}"})

        first_page = store.page(None, PAGE)
        new_order = store.insert(new_id(kind), {"item": "new-book"})

        seen = [o["id"] for o in first_page]
        cursor = first_page[-1]["id"]
        while page := store.page(cursor, PAGE):
            seen += [o["id"] for o in page]
            cursor = page[-1]["id"]
        missed += new_order["id"] not in seen
    print(f"{kind:5}  new order missed in {missed:4} of {TRIALS} runs ({missed / TRIALS:.1%})")
