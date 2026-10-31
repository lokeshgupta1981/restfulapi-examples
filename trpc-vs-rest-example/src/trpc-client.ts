import { createTRPCClient, httpBatchLink, TRPCClientError } from "@trpc/client";
import type { AppRouter } from "./trpc-server.js";

const url = process.env.TRPC_URL ?? "http://localhost:8001/trpc";

const trpc = createTRPCClient<AppRouter>({
  links: [httpBatchLink({ url })],
});

// Looks like a local function call; the type of `book` comes from the server code.
const book = await trpc.book.byId.query({ id: "1" });
console.log("byId:", book.title, "by", book.author, "-", book.priceCents, "cents");

const created = await trpc.book.create.mutate({
  title: "Designing Data-Intensive Applications",
  author: "Martin Kleppmann",
  priceCents: 4999,
});
console.log("created:", created);

// Two queries started together are sent as ONE batched HTTP request.
const [all, second] = await Promise.all([
  trpc.book.list.query(),
  trpc.book.byId.query({ id: "2" }),
]);
console.log("list:", all.length, "books; byId(2):", second.title);

try {
  await trpc.book.byId.query({ id: "99" });
} catch (err) {
  if (err instanceof TRPCClientError) {
    console.log("error:", err.data?.code, err.data?.httpStatus, "-", err.message);
  }
}
