// Plain fetch: we write the Book type ourselves and must keep it in sync with the server.
type Book = {
  id: string;
  title: string;
  author: string;
  priceCents: number;
};

const base = process.env.REST_URL ?? "http://localhost:8000";

const res = await fetch(base + "/books/1");
const book = (await res.json()) as Book; // a promise we make to the compiler, not a check
console.log("GET /books/1:", res.status, book.title, "by", book.author, "-", book.priceCents, "cents");

const created = await fetch(base + "/books", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: "Designing Data-Intensive Applications",
    author: "Martin Kleppmann",
    priceCents: 4999,
  }),
});
console.log("POST /books:", created.status, created.headers.get("location"), await created.json());

const missing = await fetch(base + "/books/99");
console.log("GET /books/99:", missing.status, await missing.json());
