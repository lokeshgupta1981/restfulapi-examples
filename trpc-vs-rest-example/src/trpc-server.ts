import { initTRPC, TRPCError } from "@trpc/server";
import * as trpcExpress from "@trpc/server/adapters/express";
import express from "express";
import { z } from "zod";
import { addBook, findBook, listBooks } from "./books.js";

const t = initTRPC.create();

// The router IS the API: every procedure has a name, an input schema and a resolver.
export const appRouter = t.router({
  book: t.router({
    list: t.procedure.query(() => listBooks()),

    byId: t.procedure
      .input(z.object({ id: z.string() }))
      .query(({ input }) => {
        const book = findBook(input.id);
        if (!book) {
          throw new TRPCError({ code: "NOT_FOUND", message: "No book with id " + input.id });
        }
        return book;
      }),

    create: t.procedure
      .input(z.object({
        title: z.string().min(1),
        author: z.string().min(1),
        priceCents: z.number().int().positive(),
      }))
      .mutation(({ input }) => addBook(input)),
  }),
});

// Only the TYPE is exported to the client. No server code is shipped to it.
export type AppRouter = typeof appRouter;

const app = express();
app.use((req, _res, next) => {
  console.log(`${req.method} ${req.originalUrl}`);
  next();
});
app.use(
  "/trpc",
  trpcExpress.createExpressMiddleware({
    router: appRouter,
    // tRPC sets no cache headers by default. We opt in for successful book queries.
    responseMeta({ paths, errors, type }) {
      const onlyBooks = paths?.every((p) => p.startsWith("book.")) ?? false;
      if (type === "query" && onlyBooks && errors.length === 0) {
        return { headers: new Headers([["cache-control", "public, max-age=60"]]) };
      }
      return {};
    },
  }),
);

const port = Number(process.env.PORT ?? 8001);
app.listen(port, () => console.log(`tRPC server on http://localhost:${port}/trpc`));
