// Two typical mistakes against the tRPC API. tsc rejects both.
import { createTRPCClient, httpBatchLink } from "@trpc/client";
import type { AppRouter } from "../trpc-server.js";

const trpc = createTRPCClient<AppRouter>({
  links: [httpBatchLink({ url: "http://localhost:8001/trpc" })],
});

const book = await trpc.book.byId.query({ id: 1 });
console.log(book.price);
