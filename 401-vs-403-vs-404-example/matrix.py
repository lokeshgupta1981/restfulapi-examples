from fastapi.testclient import TestClient
from app import app
c = TestClient(app)
callers = {"no token": None, "carol (acme, read)": "tok-carol", "alice (acme, read+write)": "tok-alice", "bob (globex admin)": "tok-bob"}
reqs = [("GET", "/projects/p-100"), ("GET", "/projects/p-101"), ("GET", "/projects/p-999"), ("GET", "/projects/p-200"), ("DELETE", "/projects/p-102"), ("GET", "/admin/audit-log")]
print("request".ljust(26) + " | ".join(callers))
for m, p in reqs:
    row = []
    for name, tok in callers.items():
        h = {"Authorization": f"Bearer {tok}"} if tok else {}
        row.append(str(c.request(m, p, headers=h).status_code).ljust(len(name)))
    print(f"{m} {p}".ljust(26) + " | ".join(row))
