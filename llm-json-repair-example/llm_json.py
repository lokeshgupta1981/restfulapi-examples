"""Parse, repair and validate JSON from an LLM reply, in that order.

parse_reply() returns one of three outcomes:
  valid     strict JSON that matches the schema
  repaired  JSON that needed json_repair and then matched the schema
  retry     truncated, unparseable or invalid data, with the reason to send back to the model
"""

import json
import math
import re
from dataclasses import dataclass, field
from typing import Literal

import json_repair
from pydantic import BaseModel, Field, ValidationError


class Item(BaseModel):
    sku: str = Field(pattern=r"^[A-Z]{2}-\d{2}$")
    qty: int = Field(ge=1)


class Order(BaseModel):
    order_id: str = Field(pattern=r"^A-\d{4}$")
    items: list[Item] = Field(min_length=1)
    total: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal["EUR", "USD"]
    gift: bool = False
    coupon: str | None = None
    note: str | None = None


@dataclass
class Result:
    outcome: Literal["valid", "repaired", "retry"]
    order: Order | None = None
    reason: str = ""
    repairs: list[str] = field(default_factory=list)


FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> tuple[str, str]:
    """Returns (candidate, repair_source) for a reply.

    candidate      the inside of a code fence, or the first { to the last }, for the strict parse
    repair_source  the same text, but up to the end of the reply, so a repair keeps a cut-off tail
    """
    fenced = FENCE.search(text)
    if fenced:
        return fenced.group(1), fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1:
        return text, text
    return (text[start:end + 1] if end > start else text[start:]), text[start:]


def reject_constant(name: str):
    raise ValueError(f"{name} is not valid JSON")  # Python accepts NaN and Infinity unless we refuse them


def parse_reply(text: str, finish_reason: str = "stop") -> Result:
    if finish_reason == "length":  # the model hit max_tokens, so the JSON is cut off
        return Result("retry", reason="The reply was cut off at the token limit. Raise max_tokens or ask for less data.")
    candidate, repair_source = extract_json(text)
    repairs = []
    try:
        data = json.loads(candidate, parse_constant=reject_constant)
    except (json.JSONDecodeError, ValueError) as error:
        data, log = json_repair.repair_json(repair_source, return_objects=True, skip_json_loads=True, logging=True)
        repairs = [f"strict parse failed: {error}"] + [entry["text"] for entry in log]
        if not isinstance(data, dict):
            return Result("retry", reason=f"No JSON object found ({error}).", repairs=repairs)
    try:
        order = Order.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
        return Result("retry", reason=f"The JSON does not match the schema: {problems}", repairs=repairs)
    return Result("repaired" if repairs else "valid", order=order, repairs=repairs)


def retry_prompt(reason: str) -> str:
    return ("Your last reply could not be used. " + reason +
            " Reply with only one JSON object that matches the schema, without code fences or comments.")
