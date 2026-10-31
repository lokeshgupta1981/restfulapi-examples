"""Why PATCH handlers use model_dump(exclude_unset=True)."""
from pydantic import BaseModel


class UpdateMeRequest(BaseModel):
    email: str | None = None
    name: str | None = None


req = UpdateMeRequest.model_validate({"name": "Alice B."})
print("model_dump()                  ", req.model_dump())
print("model_dump(exclude_unset=True)", req.model_dump(exclude_unset=True))
