"""Three ways to answer "may this user do this action on this document?".

Each function takes a user dict, an action ("read", "edit" or "delete")
and a document dict, and returns True or False.
"""

from data import TUPLES

# ---------------------------------------------------------------- RBAC
ROLE_PERMISSIONS = {
    "viewer": {"documents:read"},
    "editor": {"documents:read", "documents:edit"},
    "admin": {"documents:read", "documents:edit", "documents:delete"},
}


def rbac_allows(user, action, doc):
    # The document is not used at all: a role grants the action on every document.
    return f"documents:{action}" in ROLE_PERMISSIONS[user["role"]]


# ---------------------------------------------------------------- ABAC
def abac_allows(user, action, doc):
    if user["role"] == "admin":
        return True
    same_department = user["department"] == doc["department"]
    if action == "read":
        return same_department
    if action == "edit":
        return (user["role"] == "editor" and same_department
                and doc["status"] != "archived")
    if action == "delete":
        return user["id"] == doc["owner"]
    return False


# ---------------------------------------------------------------- ReBAC
# For each object type and relation, the ways a subject can get that relation:
#   "direct"            a tuple (object, relation, subject) exists
#   ("self", r)         the subject has relation r on the same object
#   ("parent", r)       the subject has relation r on the object's parent
#   ("org", r)          the subject has relation r on the object's organisation
MODEL = {
    "org": {"admin": ["direct"]},
    "group": {"member": ["direct"]},
    "folder": {
        "admin": [("org", "admin")],
        "editor": ["direct", ("self", "admin")],
        "viewer": ["direct", ("self", "editor")],
    },
    "document": {
        "owner": ["direct"],
        "editor": ["direct", ("self", "owner"), ("parent", "editor")],
        "viewer": ["direct", ("self", "editor"), ("parent", "viewer")],
        "can_delete": [("self", "owner"), ("parent", "admin")],
    },
}

# Which relation an API action needs on a document.
ACTION_TO_RELATION = {"read": "viewer", "edit": "editor", "delete": "can_delete"}


def check(obj, relation, subject):
    """Return the path that proves subject has relation on obj, or None."""
    obj_type = obj.split(":")[0]
    for rule in MODEL[obj_type][relation]:
        if rule == "direct":
            for (o, r, s) in TUPLES:
                if o != obj or r != relation:
                    continue
                if s == subject:
                    return [f"{obj}#{relation}@{s}"]
                if "#" in s:  # a userset such as group:marketing#member
                    set_obj, set_rel = s.split("#")
                    path = check(set_obj, set_rel, subject)
                    if path:
                        return path + [f"{obj}#{relation}@{s}"]
        elif rule[0] == "self":
            path = check(obj, rule[1], subject)
            if path:
                return path + [f"{obj}#{relation} (because {rule[1]})"]
        else:  # follow a link such as parent or org, then check there
            link, target_rel = rule
            for (o, r, s) in TUPLES:
                if o == obj and r == link:
                    path = check(s, target_rel, subject)
                    if path:
                        return path + [f"{obj}#{relation} (via {link} {s})"]
    return None


def rebac_allows(user, action, doc):
    relation = ACTION_TO_RELATION[action]
    return check(f"document:{doc['id']}", relation, f"user:{user['id']}") is not None


# ---------------------------------------------------------------- ReBAC + an attribute rule
def hybrid_allows(user, action, doc):
    # Relationships decide who; one attribute rule decides when.
    if action == "edit" and doc["status"] == "archived":
        return False
    return rebac_allows(user, action, doc)


MODELS = {"rbac": rbac_allows, "abac": abac_allows, "rebac": rebac_allows,
          "hybrid": hybrid_allows}
