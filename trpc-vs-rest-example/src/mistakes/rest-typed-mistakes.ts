// The same two mistakes with types generated from openapi.yaml. tsc rejects both.
import createClient from "openapi-fetch";
import type { paths } from "../rest-api-types.js";

const api = createClient<paths>({ baseUrl: "http://localhost:8000" });

const { data: book } = await api.GET("/books/{id}", { params: { path: { id: 1 } } });
console.log(book?.price);
