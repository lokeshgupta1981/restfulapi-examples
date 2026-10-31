"""Tests an API for mass assignment.

Reads the current user, then tries to change every field it sees (plus a
few common guesses) with PATCH, and reads the user again to see what stuck.

    python probe.py http://localhost:8000 2
"""
import sys

import httpx

GUESSES = ["password", "is_admin", "admin", "is_staff", "verified", "balance", "account_id"]


def new_value(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 999
    if value == "customer":
        return "admin"
    return f"probe-{value}"


def main(base: str, user_id: str):
    headers = {"X-User-Id": user_id}
    with httpx.Client(base_url=base, headers=headers) as api:
        before = api.get("/users/me").json()
        fields = list(dict.fromkeys([f for f in before if f != "id"] + GUESSES))
        for field in fields:
            value = new_value(before.get(field, True))
            r = api.patch("/users/me", json={field: value})
            after = api.get("/users/me").json()
            if r.status_code >= 400:
                result = f"rejected (HTTP {r.status_code})"
            elif after.get(field) == value:
                result = "WRITABLE"
            else:
                result = f"ignored (HTTP {r.status_code})"
            print(f"{field:15} {result}")
            if field in before:
                api.patch("/users/me", json={field: before[field]})  # undo


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
