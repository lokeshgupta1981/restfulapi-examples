"""Build a Chat Completions tool definition from one OpenAPI operation.

Usage: python openapi_tools.py cancelOrder
Reads the OpenAPI document that FastAPI serves at /openapi.json.
"""
import json
import os
import sys

import httpx

ORDERS_API_URL = os.environ.get("ORDERS_API_URL", "http://127.0.0.1:8780")


def resolve(schema: dict, document: dict) -> dict:
    """Replace a local $ref such as #/components/schemas/CancelRequest with its target."""
    if "$ref" in schema:
        target = document
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return resolve(target, document)
    return schema


def clean(schema: dict) -> dict:
    """Keep only the keywords a model needs; drop FastAPI's generated titles."""
    return {k: v for k, v in schema.items() if k in ("type", "description", "enum", "minimum", "pattern", "format")}


def operation_to_tool(document: dict, operation_id: str) -> tuple[dict, dict]:
    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            if operation.get("operationId") != operation_id:
                continue
            properties, required = {}, []
            for param in operation.get("parameters", []):
                if param["in"] not in ("path", "query"):
                    continue  # headers such as Idempotency-Key are set by our code, not the model
                properties[param["name"]] = clean(resolve(param["schema"], document))
                required.append(param["name"])
            body = operation.get("requestBody", {}).get("content", {}).get("application/json")
            if body:
                body_schema = resolve(body["schema"], document)
                for name, prop in body_schema.get("properties", {}).items():
                    properties[name] = clean(resolve(prop, document))
                    required.append(name)
            tool = {
                "type": "function",
                "function": {
                    "name": operation_id,
                    "description": operation.get("summary", ""),
                    "strict": True,
                    "parameters": {"type": "object", "properties": properties,
                                   "required": required, "additionalProperties": False},
                },
            }
            return tool, {"method": method.upper(), "path": path}
    raise KeyError(operation_id)


if __name__ == "__main__":
    openapi = httpx.get(f"{ORDERS_API_URL}/openapi.json").json()
    print("openapi:", openapi["openapi"])
    tool, http = operation_to_tool(openapi, sys.argv[1])
    print("http:", json.dumps(http))
    print(json.dumps(tool, indent=2))
