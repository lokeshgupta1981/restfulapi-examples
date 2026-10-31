Source code for the article [RBAC vs ABAC vs ReBAC for API Authorization](https://restfulapi.net/rbac-vs-abac-api-authorization/)

# RBAC vs ABAC vs ReBAC example

A small Docs API (FastAPI) whose read, edit and delete endpoints can be protected by four authorization models: role-based (RBAC), attribute-based (ABAC), relationship-based (ReBAC), or a remote Policy Decision Point that speaks the OpenID AuthZEN Authorization API 1.0. The same ten requests show where each model gives the wrong answer.

## Files

| File | What it does |
|---|---|
| data.py | Demo users (role and department), demo tokens, three documents and the ReBAC relationship tuples |
| policies.py | *rbac_allows()*, *abac_allows()*, *rebac_allows()* with a small tuple walker (*check()*), and *hybrid_allows()* (ReBAC plus one attribute rule) |
| app.py | The Docs API. *AUTHZ_MODEL* = rbac, abac, rebac, hybrid or authzen. Unknown or unreadable documents return 404, readable but forbidden actions return 403 |
| pdp.py | AuthZEN PDP: POST /access/v1/evaluation, POST /access/v1/evaluations, GET /.well-known/authzen-configuration. *PDP_MODEL* picks the policy |
| matrix.py | Prints each model's decision for ten requests next to the wanted decision, and the ReBAC proof paths (no server needed) |
| demo.sh | Five curl calls against the API |
| pdp_demo.sh | AuthZEN calls straight to the PDP |
| run_all.sh | Runs matrix.py, demo.sh for rbac, abac, rebac and authzen, pdp_demo.sh and pytest |
| test_authz.py | pytest tests |

## Demo users

| Token | User | Role | Department | Relationships (ReBAC) |
|---|---|---|---|---|
| tok-alice | alice | editor | marketing | owns launch-plan and brand-guide, editor of folder marketing-q4, viewer of pricing-2027 |
| tok-bob | bob | editor | sales | owns pricing-2027 |
| tok-carol | carol | viewer | marketing | member of group marketing |
| tok-dave | dave | admin | it | admin of org acme |
| tok-erin | erin | viewer | agency | viewer of folder marketing-q4 |

Tokens, users and the PDP key *demo-pep-key-not-secret* are demo values only. Never use them in production.

## Versions

- Python 3.13 (3.10 or later)
- fastapi 0.143.0
- uvicorn 0.54.0
- httpx2 2.13.1 (PDP client and the FastAPI TestClient)
- pytest 9.1.1
- curl

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/rbac-vs-abac-api-authorization-example
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python matrix.py
./run_all.sh                      # uses ports 8000 (API) and 8001 (PDP)
API_PORT=9000 PDP_PORT=9001 ./run_all.sh

# or by hand
PDP_MODEL=hybrid uvicorn pdp:app --port 8001                         # terminal 1
AUTHZ_MODEL=authzen PDP_URL=http://127.0.0.1:8001 uvicorn app:app --port 8000   # terminal 2
./demo.sh && ./pdp_demo.sh                                           # terminal 3
pytest -q
```

OUTPUTS.txt holds the output of one run of run_all.sh on Linux (2026-10-31).
