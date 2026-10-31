// The same two mistakes against the REST API with a hand-written type.
// The type was written when the field was still called "price".
type Book = { id: string; title: string; author: string; price: number };

const base = process.env.REST_URL ?? "http://localhost:8000";
const id = 1;
const res = await fetch(base + "/books/" + id);
const book = (await res.json()) as Book;
console.log(book.price);
