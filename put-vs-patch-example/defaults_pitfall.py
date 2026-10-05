from typing import Optional
from pydantic import BaseModel


class TicketWithDefaults(BaseModel):
    title: str = ""
    status: str = "open"
    priority: str = "normal"
    assignee: Optional[str] = None
    labels: list[str] = []


stored = {"title": "Checkout page times out", "status": "open",
          "priority": "normal", "assignee": "maria", "labels": ["checkout"]}

put_body = TicketWithDefaults.model_validate({"status": "closed"})
print("PUT stores:  ", put_body.model_dump())

patch_body = TicketWithDefaults.model_validate({"status": "closed"})
changes = patch_body.model_dump(exclude_unset=True)
print("PATCH changes:", changes)
print("PATCH stores:", {**stored, **changes})
