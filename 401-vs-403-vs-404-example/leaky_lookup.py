"""The wrong way: load by ID first, compare the tenant afterwards. Run: python leaky_lookup.py"""
from app import PROJECTS, TOKENS, not_found, problem


def get_project_leaky(project_id, caller):
    project = PROJECTS.get(project_id)
    if project is None:
        return not_found(project_id)
    if project["tenant"] != caller["tenant"]:
        return problem(403, "Forbidden", "Not your tenant")
    return {"id": project_id, **project}


if __name__ == "__main__":
    alice = TOKENS["tok-alice"]
    for project_id in ("p-999", "p-200"):
        response = get_project_leaky(project_id, alice)
        print(project_id, response.status_code, response.body.decode())
