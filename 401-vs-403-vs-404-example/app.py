"""Projects API that returns HTTP 401, 403 or 404 for the right reasons."""
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException

app = FastAPI()

REALM = "projects-api"
PUBLIC_PATHS = {"/health", "/token"}

# Demo access tokens. A real API validates a JWT or calls an introspection endpoint.
TOKENS = {
    "tok-alice": {"user": "alice", "tenant": "acme", "role": "member",
                  "scopes": {"projects:read", "projects:write"}, "exp": 4102444800},
    "tok-carol": {"user": "carol", "tenant": "acme", "role": "member",
                  "scopes": {"projects:read"}, "exp": 4102444800},
    "tok-bob": {"user": "bob", "tenant": "globex", "role": "admin",
                "scopes": {"projects:read", "projects:write"}, "exp": 4102444800},
    "tok-dave": {"user": "dave", "tenant": "acme", "role": "member",
                 "scopes": {"projects:read"}, "exp": 4102444800, "suspended": True},
    "tok-alice-old": {"user": "alice", "tenant": "acme", "role": "member",
                      "scopes": {"projects:read", "projects:write"}, "exp": 1767225600},
}
REFRESH_TOKENS = {"rt-alice": "tok-alice"}

PROJECTS = {
    "p-100": {"tenant": "acme", "owner": "alice", "private": False, "name": "Website redesign"},
    "p-101": {"tenant": "acme", "owner": "alice", "private": True, "name": "Salary review"},
    "p-102": {"tenant": "acme", "owner": "erin", "private": False, "name": "Mobile app"},
    "p-200": {"tenant": "globex", "owner": "bob", "private": False, "name": "Globex billing"},
}


def problem(status, title, detail, headers=None):
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, headers=headers,
                        media_type="application/problem+json")


def unauthorized(detail, error=None):
    challenge = f'Bearer realm="{REALM}"'
    if error:
        challenge += f', error="{error}", error_description="{detail}"'
    return problem(401, "Unauthorized", detail, {"WWW-Authenticate": challenge})


def not_found(project_id):
    # One body for "does not exist" and "you may not know it exists".
    return problem(404, "Not Found", f"Project {project_id} not found")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    # Unknown paths get the same Problem Details shape as everything else.
    return problem(exc.status_code, exc.detail, f"No resource at {request.url.path}")


@app.middleware("http")
async def authenticate(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    header = request.headers.get("authorization")
    if header is None:
        return unauthorized("No credentials")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return unauthorized("Use the Bearer scheme")
    if not token or " " in token.strip():
        return problem(400, "Bad Request", "Malformed Authorization header",
                       {"WWW-Authenticate": f'Bearer realm="{REALM}", error="invalid_request"'})
    caller = TOKENS.get(token.strip())
    if caller is None:
        return unauthorized("Unknown access token", "invalid_token")
    if caller["exp"] < time.time():
        return unauthorized("The access token expired", "invalid_token")
    if caller.get("suspended"):
        return problem(403, "Forbidden", "Account suspended")
    request.state.caller = caller
    return await call_next(request)


def visible_project(project_id, caller):
    """Find a project with one scoped query: WHERE id = ? AND tenant = ? AND (not private OR owner = ?)."""
    matches = [project for pid, project in PROJECTS.items()
               if pid == project_id
               and project["tenant"] == caller["tenant"]
               and (not project["private"] or project["owner"] == caller["user"])]
    return matches[0] if matches else None


@app.get("/health")
def health():
    return {"status": "UP"}


@app.post("/token")
async def token(request: Request):
    form = (await request.body()).decode()
    refresh_token = dict(p.split("=", 1) for p in form.split("&") if "=" in p).get("refresh_token")
    access_token = REFRESH_TOKENS.get(refresh_token)
    if access_token is None:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": 3600}


@app.get("/projects/{project_id}")
def get_project(project_id: str, request: Request):
    project = visible_project(project_id, request.state.caller)
    if project is None:
        return not_found(project_id)
    return {"id": project_id, **project}


@app.delete("/projects/{project_id}")
def delete_project(project_id: str, request: Request):
    caller = request.state.caller
    # 1. Token-level check: does not depend on the project, so it reveals nothing.
    if "projects:write" not in caller["scopes"]:
        return problem(403, "Forbidden", "The token lacks the projects:write scope",
                       {"WWW-Authenticate": f'Bearer realm="{REALM}", error="insufficient_scope", '
                                            'scope="projects:write"'})
    # 2. Existence check, scoped to what the caller may see.
    project = visible_project(project_id, caller)
    if project is None:
        return not_found(project_id)
    # 3. Object-level check: the caller can see the project but not delete it.
    if project["owner"] != caller["user"] and caller["role"] != "admin":
        return problem(403, "Forbidden", "Only the owner or an admin can delete this project")
    PROJECTS.pop(project_id)
    return Response(status_code=204)


@app.get("/admin/audit-log")
def audit_log(request: Request):
    if request.state.caller["role"] != "admin":
        return problem(403, "Forbidden", "Admin role required")
    return {"entries": []}
