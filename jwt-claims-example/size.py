"""Measure how claims grow the token that travels in every Authorization header."""
from tokens import make_token

minimal = make_token(drop=["nbf", "client_id", "https://bookstore.example/claims/tenant", "plan"],
                     scope="orders:read")
ours = make_token()
fat = make_token(
    name="Jane Example", email="jane@example.com", address="1 Demo Street, Springfield",
    permissions=[f"orders:action-{i}" for i in range(40)],
    groups=[f"group-{i}" for i in range(20)],
)
for label, token in [("only what the API checks", minimal),
                     ("our demo token", ours),
                     ("profile + 40 permissions + 20 groups", fat)]:
    print(f"{label:<40} {len(token):>5} characters")
