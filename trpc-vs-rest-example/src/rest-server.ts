import express from "express";
import { z } from "zod";
import { addBook, findBook, listBooks } from "./books.js";

const NewBook = z.object({
  title: z.string().min(1),
  author: z.string().min(1),
  priceCents: z.number().int().positive(),
});

const app = express();
app.use(express.json());
app.use((req, _res, next) => {
  console.log(`${req.method} ${req.originalUrl}`);
  next();
});

// Resources and HTTP methods: the URL names the thing, the method names the action.
app.get("/books", (_req, res) => {
  res.set("Cache-Control", "public, max-age=60").json(listBooks());
});

app.get("/books/:id", (req, res) => {
  const book = findBook(req.params.id);
  if (!book) {
    res.status(404).json({ error: "No book with id " + req.params.id });
    return;
  }
  res.set("Cache-Control", "public, max-age=60").json(book);
});

app.post("/books", (req, res) => {
  const parsed = NewBook.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid book", issues: parsed.error.issues });
    return;
  }
  const book = addBook(parsed.data);
  res.status(201).location("/books/" + book.id).json(book);
});

const port = Number(process.env.PORT ?? 8000);
app.listen(port, () => console.log(`REST server on http://localhost:${port}`));
