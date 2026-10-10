"""Runs one HTTP test per checklist item against a running orders API.
The number in brackets is the item number in the article's 13-item checklist.

Usage: python security_check.py http://127.0.0.1:8001
Each test logs in as alice (and bob or admin when needed) and tries one attack.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"


def call(method, path, token=None, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read().decode()


def login(name):
    status, _, body = call("POST", "/login", body={"name": name, "password": name + "-pass"})
    return json.loads(body)["token"]


def check_bola(alice):
    status, _, _ = call("GET", "/orders/201", alice)  # order 201 belongs to bob
    return status == 404, f"alice reads bob's order 201 -> HTTP {status}"


def check_mass_assignment(alice):
    status, _, body = call("PATCH", "/users/me", alice, {"email": "a@example.com", "role": "admin"})
    escalated = status == 200 and json.loads(body).get("role") == "admin"
    return not escalated, f"alice sends role=admin -> HTTP {status}" + (", role is now admin" if escalated else "")


def check_admin_route(bob):
    status, _, _ = call("GET", "/admin/users", bob)
    return status == 403, f"bob calls GET /admin/users -> HTTP {status}"


def check_sql_injection(bob):
    status, _, body = call("GET", "/orders?item=x%27%20OR%20%271%27=%271", bob)
    leaked = status == 200 and any(o["id"] != 201 for o in json.loads(body))
    return not leaked, f"bob searches item=x' OR '1'='1 -> HTTP {status}, {len(json.loads(body)) if status == 200 else 0} orders"


def check_login_limit(_):
    codes = [call("POST", "/login", body={"name": "alice", "password": "guess"})[0] for _ in range(8)]
    return 429 in codes, f"8 wrong passwords -> {codes}"


def check_error_details(alice):
    status, _, body = call("PATCH", "/users/me", alice, {"no_such_column": 1})
    return "Traceback" not in body and "sqlite3" not in body, f"bad field -> HTTP {status}, body {body[:60]}"


def check_cors(_):
    _, headers, _ = call("GET", "/orders/101", headers={"Origin": "https://evil.example"})
    allowed = headers.get("access-control-allow-origin") or headers.get("Access-Control-Allow-Origin")
    return allowed != "https://evil.example", f"Origin evil.example -> Access-Control-Allow-Origin: {allowed}"


CHECKS = [("[2] Object-level authorization (BOLA)", check_bola, "alice"),
          ("[4] Mass assignment", check_mass_assignment, "alice"),
          ("[3] Function-level authorization", check_admin_route, "bob"),
          ("[6] SQL injection", check_sql_injection, "bob"),
          ("[10] Error details", check_error_details, "alice"),
          ("[9] CORS", check_cors, None),
          ("[7] Login rate limit", check_login_limit, None)]  # last, because it locks alice out

if __name__ == "__main__":
    passed = 0
    for title, check, who in CHECKS:
        ok, detail = check(login(who) if who else None)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {title:<39} {detail}")
    print(f"{passed}/{len(CHECKS)} checks passed")
    sys.exit(0 if passed == len(CHECKS) else 1)
