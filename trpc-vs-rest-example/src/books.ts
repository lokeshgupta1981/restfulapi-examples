// In-memory bookstore shared by the tRPC server and the REST server,
// so both APIs return exactly the same data.
export type Book = {
  id: string;
  title: string;
  author: string;
  priceCents: number;
};

const books = new Map<string, Book>([
  ["1", { id: "1", title: "Clean Code", author: "Robert C. Martin", priceCents: 3999 }],
  ["2", { id: "2", title: "Refactoring", author: "Martin Fowler", priceCents: 4499 }],
]);

let nextId = 3;

export function listBooks(): Book[] {
  return [...books.values()];
}

export function findBook(id: string): Book | undefined {
  return books.get(id);
}

export function addBook(data: Omit<Book, "id">): Book {
  const book = { id: String(nextId++), ...data };
  books.set(book.id, book);
  return book;
}
