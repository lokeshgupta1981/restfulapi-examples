"""What Pydantic does with a field the model does not declare."""
from pydantic import BaseModel, ConfigDict, ValidationError

payload = {"name": "Mallory", "role": "admin"}

for mode in ("ignore", "forbid", "allow"):
    class UpdateMe(BaseModel):
        model_config = ConfigDict(extra=mode)
        name: str

    try:
        print(f"{mode:7}", UpdateMe.model_validate(payload).model_dump())
    except ValidationError as e:
        err = e.errors()[0]
        print(f"{mode:7}", err["type"], err["loc"], err["msg"])
