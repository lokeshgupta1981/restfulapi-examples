"""Print the decision of each model for ten requests, next to what the business wants.

No server needed: python matrix.py
"""

from data import DOCUMENTS, USERS
from policies import MODELS, check

# (user, action, document, wanted, why)
CASES = [
    ("carol", "read", "launch-plan", True, "her team's document"),
    ("carol", "edit", "launch-plan", False, "she is a viewer"),
    ("bob", "read", "launch-plan", False, "another team's document"),
    ("bob", "edit", "launch-plan", False, "another team's document"),
    ("alice", "delete", "launch-plan", True, "she owns it"),
    ("alice", "edit", "brand-guide", False, "archived document"),
    ("erin", "read", "launch-plan", True, "folder shared with the agency"),
    ("erin", "read", "pricing-2027", False, "not shared with her"),
    ("alice", "read", "pricing-2027", True, "Bob shared this one file"),
    ("dave", "delete", "pricing-2027", True, "admin"),
]


def mark(decision, wanted):
    text = "allow" if decision else "deny"
    return text if decision == wanted else text + " (wrong)"


def main():
    print(f"{'Request':<30} {'Wanted':<7} {'RBAC':<14} {'ABAC':<14} {'ReBAC':<14} {'ReBAC+rule':<14}")
    wrong = {name: 0 for name in MODELS}
    for user, action, doc_id, wanted, why in CASES:
        row = f"{user + ' ' + action + ' ' + doc_id:<30} {'allow' if wanted else 'deny':<7}"
        for name, allows in MODELS.items():
            decision = allows(USERS[user], action, DOCUMENTS[doc_id])
            wrong[name] += decision != wanted
            row += f" {mark(decision, wanted):<14}"
        print(row)
    print(f"{'Wrong decisions':<38} " + " ".join(f"{n:<14}" for n in wrong.values()))

    print("\nWhy ReBAC lets Erin read launch-plan:")
    for step in check("document:launch-plan", "viewer", "user:erin"):
        print("  " + step)

    print("\nWhy ReBAC lets Carol read launch-plan:")
    for step in check("document:launch-plan", "viewer", "user:carol"):
        print("  " + step)

    print("\nWhy ReBAC lets Dave delete pricing-2027:")
    for step in check("document:pricing-2027", "can_delete", "user:dave"):
        print("  " + step)


if __name__ == "__main__":
    main()
