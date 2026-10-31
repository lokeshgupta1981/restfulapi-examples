"""Demo data for the Docs API: users, tokens, documents and relationship tuples.

Everything lives in memory and is for the demo only.
"""

# Demo bearer tokens. Not real secrets.
TOKENS = {
    "tok-alice": "alice",
    "tok-bob": "bob",
    "tok-carol": "carol",
    "tok-dave": "dave",
    "tok-erin": "erin",
}

# Subject attributes (used by RBAC and ABAC).
USERS = {
    "alice": {"id": "alice", "role": "editor", "department": "marketing"},
    "bob": {"id": "bob", "role": "editor", "department": "sales"},
    "carol": {"id": "carol", "role": "viewer", "department": "marketing"},
    "dave": {"id": "dave", "role": "admin", "department": "it"},
    "erin": {"id": "erin", "role": "viewer", "department": "agency"},
}

# Resource attributes (used by ABAC). ReBAC uses the tuples below instead.
DOCUMENTS = {
    "launch-plan": {"id": "launch-plan", "title": "Q4 launch plan", "owner": "alice",
                    "department": "marketing", "status": "draft"},
    "brand-guide": {"id": "brand-guide", "title": "Brand guide 2025", "owner": "alice",
                    "department": "marketing", "status": "archived"},
    "pricing-2027": {"id": "pricing-2027", "title": "Pricing 2027", "owner": "bob",
                     "department": "sales", "status": "draft"},
}

# Relationship tuples for ReBAC: (object, relation, subject).
# A subject is a user ("user:alice") or a set of users ("group:marketing#member").
TUPLES = [
    ("group:marketing", "member", "user:alice"),
    ("group:marketing", "member", "user:carol"),
    ("group:sales", "member", "user:bob"),
    ("org:acme", "admin", "user:dave"),

    ("folder:marketing-q4", "org", "org:acme"),
    ("folder:marketing-q4", "editor", "user:alice"),
    ("folder:marketing-q4", "viewer", "group:marketing#member"),
    ("folder:marketing-q4", "viewer", "user:erin"),          # shared with the agency
    ("folder:sales", "org", "org:acme"),
    ("folder:sales", "viewer", "group:sales#member"),

    ("document:launch-plan", "parent", "folder:marketing-q4"),
    ("document:launch-plan", "owner", "user:alice"),
    ("document:brand-guide", "parent", "folder:marketing-q4"),
    ("document:brand-guide", "owner", "user:alice"),
    ("document:pricing-2027", "parent", "folder:sales"),
    ("document:pricing-2027", "owner", "user:bob"),
    ("document:pricing-2027", "viewer", "user:alice"),       # Bob shared one file with Alice
]
