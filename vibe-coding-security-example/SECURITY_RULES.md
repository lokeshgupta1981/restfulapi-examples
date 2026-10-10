# Security rules for API code

Copy these rules into the instruction file of your coding agent (AGENTS.md, CLAUDE.md, .cursor/rules or .github/copilot-instructions.md).

- Every route that reads or changes data requires authentication. List public routes explicitly.
- Every query for a user-owned record filters by the caller's ID. Return 404 when the record belongs to someone else.
- Admin routes check the caller's role on the server, in a shared dependency or middleware.
- Request bodies use explicit schemas that reject unknown fields. Never copy a request body into a database row or ORM object.
- Validate types, lengths and ranges of all input. Set a maximum page size.
- Build SQL only with parameters. Never format user input into SQL, shell commands or file paths.
- Limit login, signup, password reset and other expensive endpoints, and return 429 with Retry-After.
- Read secrets from environment variables or a secret manager. Never write keys, tokens or passwords into source code, logs or client bundles.
- CORS allows only the known front-end origins. Never combine a wildcard or reflected origin with credentials.
- Error responses never contain stack traces, SQL or internal paths. Log the details on the server.
- Fetch URLs from user input only through an allow list of hosts.
- Add a dependency only after checking that the package exists on the official registry and is the one you mean.
- For every new route, add a test where user B tries to read and change user A's data.
