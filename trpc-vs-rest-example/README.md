Source code for the article [tRPC vs REST: When to Use Each for a TypeScript API](https://restfulapi.net/trpc-vs-rest/)

One small bookstore API built twice: once with tRPC and once as a REST API with Express. Both servers use the same in-memory data (`src/books.ts`), so we can compare the requests on the wire, the error responses, caching headers, batching, and what the TypeScript compiler catches in each client.

## Versions
- Node.js 22.23, TypeScript 5.9.3, tsx 4.23.15
- @trpc/server and @trpc/client 11.22.1, zod 4.6.7, express 5.3.0
- openapi-typescript 7.13.0 and openapi-fetch 0.17.0 (typed REST client generated from `openapi.yaml`)

## Files
- `src/books.ts`: the shared in-memory bookstore (2 books to start with)
- `src/trpc-server.ts`: tRPC router `book.list`, `book.byId`, `book.create` on Express, path `/trpc`, port 8001
- `src/trpc-client.ts`: tRPC client with `httpBatchLink`
- `src/rest-server.ts`: REST API `GET /books`, `GET /books/:id`, `POST /books`, port 8000
- `src/rest-client.ts`: REST client with `fetch` and a hand-written `Book` type
- `openapi.yaml`: OpenAPI 3.1 description of the REST API
- `src/rest-api-types.ts`: types generated from `openapi.yaml` (`npm run rest:types`)
- `src/rest-typed-client.ts`: REST client with the generated types and openapi-fetch
- `src/mistakes/`: the same two client mistakes against each API, to see which ones `tsc` catches
- `demo.sh`: curl requests to both servers, the clients, and both type checks
- `OUTPUTS.txt`: the captured output of `demo.sh`

## Run
```
npm install

# Terminal 1 and 2 (PORT is optional)
PORT=8000 npm run rest:server
PORT=8001 npm run trpc:server

# Terminal 3
./demo.sh                          # or REST_PORT=... TRPC_PORT=... ./demo.sh

npm run typecheck                  # the normal code: no errors
npm run typecheck:mistakes         # 4 errors, all in the tRPC and OpenAPI-typed files
```

Start the servers with `NODE_ENV=production` to leave the stack trace out of tRPC error responses, as in `OUTPUTS.txt`.
`demo.sh` needs bash and curl; on Windows, run it from Git Bash or WSL.
