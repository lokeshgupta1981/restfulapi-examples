"""Tool definitions for the Orders API, written by hand.

TOOLS goes to the model in the Chat Completions "tools" field.
OPERATIONS is the allow list: the only HTTP calls the client will ever make.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Get one order by its numeric ID. Returns status, customer, total and currency.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "minimum": 1, "description": "Numeric order ID, for example 1001"}
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment",
            "description": "Get the carrier, tracking number and estimated delivery date of one order.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "minimum": 1, "description": "Numeric order ID"}
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an order that has not shipped yet. Ask the user before calling this tool.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "minimum": 1, "description": "Numeric order ID"},
                    "reason": {"type": "string", "description": "Short reason given by the customer"},
                },
                "required": ["order_id", "reason"],
                "additionalProperties": False,
            },
        },
    },
]

OPERATIONS = {
    "get_order": {"method": "GET", "path": "/orders/{order_id}", "write": False},
    "get_shipment": {"method": "GET", "path": "/orders/{order_id}/shipment", "write": False},
    "cancel_order": {"method": "POST", "path": "/orders/{order_id}/cancel", "write": True, "body": ["reason"]},
}

SCHEMAS = {tool["function"]["name"]: tool["function"]["parameters"] for tool in TOOLS}
