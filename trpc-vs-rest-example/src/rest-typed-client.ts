// REST with types generated from openapi.yaml (npm run rest:types).
import createClient from "openapi-fetch";
import type { paths } from "./rest-api-types.js";

const api = createClient<paths>({ baseUrl: process.env.REST_URL ?? "http://localhost:8000" });

const { data: book, response } = await api.GET("/books/{id}", { params: { path: { id: "1" } } });
if (book) {
  console.log("typed GET /books/1:", response.status, book.title, "-", book.priceCents, "cents");
}
