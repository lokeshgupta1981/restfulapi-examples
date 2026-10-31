Source code for the article [Mass Assignment Vulnerability in REST APIs](https://restfulapi.net/mass-assignment-rest-api/)

# Mass assignment example

A small bookstore users API in Python (FastAPI, SQLAlchemy, SQLite), in two versions:

- `vulnerable_app.py` binds the raw JSON body to the database model (`User(**body)` and a `setattr()` loop). A client can set `role`, `store_credit`, `email_verified` and even `id`, and the responses include the password. Do not copy it.
- `secure_app.py` binds every request to a DTO (a Pydantic model with `extra="forbid"`) that lists only the fields the endpoint accepts. Unknown fields get HTTP 422. `PATCH /admin/users/{id}` uses a separate DTO for `role` and `store_credit` and answers HTTP 403 to non-admins. Responses use a `UserResponse` DTO without the password.

Both apps identify the caller with an `X-User-Id` header to keep the demo short. A real API reads the user from a verified token. Each app recreates its SQLite database on start and adds one admin (id 1). The passwords are demo values stored in plain text; store a hash in real code.

## Files

- `models.py`: the `User` model shared by both apps.
- `vulnerable_app.py`, `secure_app.py`: the two apps.
- `demo.sh`: the same curl requests against both apps (sign-up with `role: admin`, PATCH with `store_credit`, a whole object sent back, admin endpoint as customer and as admin).
- `probe.py`: reads the current user, tries to change every field it sees plus a few guesses with PATCH, and reports which ones stuck.
- `test_mass_assignment.py`: pytest regression test that tries to set server-owned fields. Passes on the secure app, fails on purpose with `APP=vulnerable_app`.
- `extra_modes.py`: what Pydantic does with an unknown field under `extra="ignore"`, `"forbid"` and `"allow"`.
- `patch_unset.py`: why PATCH handlers use `model_dump(exclude_unset=True)`.
- `frameworks/express/`: the same bug (`Object.assign(user, req.body)`) and an allow-list fix in Express.
- `frameworks/spring/`: Spring Boot, `@RequestBody User` (vulnerable) and `@RequestBody SignUpRequest` (record DTO), with `spring.jackson.deserialization.fail-on-unknown-properties=true`.
- `frameworks/django/`: Django REST Framework, `ModelSerializer` with `fields = "__all__"` vs an explicit field list with `read_only_fields`. Runs without a server.
- `OUTPUTS.txt`: output of everything above from a real run.

## Versions

- Python 3.13 (3.10 or later works); fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.13.5, SQLAlchemy 2.1.6, httpx 0.28.1, pytest 9.1.1 (pinned in `requirements.txt`)
- Node.js 22 with express 5.3.0
- Java 25 and Maven 3.9 with Spring Boot 4.1.2
- Django 6.1.2 and djangorestframework 3.18.3 (pinned in `frameworks/django/requirements.txt`)
- curl and bash for `demo.sh` (on Windows, use Git Bash or WSL)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/mass-assignment-rest-api-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn vulnerable_app:app --port 8000   # terminal 1
uvicorn secure_app:app --port 8001       # terminal 2
./demo.sh                                # terminal 3
python probe.py http://localhost:8000 2  # after demo.sh created user 2
python probe.py http://localhost:8001 2
pytest -q test_mass_assignment.py
APP=vulnerable_app pytest -q test_mass_assignment.py   # fails on purpose
```

Restart both apps before running `demo.sh` again; they start with an empty database. To use other ports, start uvicorn with another `--port` and run `VULN=http://localhost:9000 SECURE=http://localhost:9001 ./demo.sh`.

Express:

```bash
cd frameworks/express
npm install
node app.js                      # PORT=3000 by default
curl -X PATCH http://localhost:3000/users/2 -H 'Content-Type: application/json' -d '{"name":"Alice B.","role":"admin"}'
curl -X PATCH http://localhost:3000/vulnerable/users/2 -H 'Content-Type: application/json' -d '{"name":"Alice B.","role":"admin"}'
```

Spring Boot:

```bash
cd frameworks/spring
mvn package
java -jar target/mass-assignment-spring-1.0.0.jar     # PORT=8080 by default
curl -X POST http://localhost:8080/vulnerable/users -H 'Content-Type: application/json' -d '{"email":"mallory@example.com","name":"Mallory","password":"mallory-pass-1","role":"admin","storeCredit":500}'
curl -X POST http://localhost:8080/users -H 'Content-Type: application/json' -d '{"email":"mallory@example.com","name":"Mallory","password":"mallory-pass-1","role":"admin","storeCredit":500}'
```

Start it with `--spring.jackson.deserialization.fail-on-unknown-properties=false` to see the Spring Boot default, which ignores the unknown `role` field instead of answering HTTP 400.

Django REST Framework:

```bash
cd frameworks/django
pip install -r requirements.txt
python serializers_demo.py
```
