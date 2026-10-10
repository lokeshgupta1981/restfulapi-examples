"""Model replies collected as test cases. Each one asks for the same order as JSON."""

VALID = '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2}], "total": 59.9, "currency": "EUR"}'

CASES = {
    "valid JSON": VALID,
    "markdown fence": "```json\n" + VALID + "\n```",
    "prose around JSON": "Sure! Here is the order:\n" + VALID + "\nLet me know if you need anything else.",
    "trailing comma": '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2},], "total": 59.9, "currency": "EUR",}',
    "single quotes": "{'order_id': 'A-1001', 'items': [{'sku': 'KB-01', 'qty': 2}], 'total': 59.9, 'currency': 'EUR'}",
    "Python literals": '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2}], "total": 59.9, "currency": "EUR", "gift": True, "coupon": None}',
    "comments": '{\n  "order_id": "A-1001", // from the subject line\n  "items": [{"sku": "KB-01", "qty": 2}],\n  "total": 59.9,\n  "currency": "EUR"\n}',
    "unquoted keys": '{order_id: "A-1001", items: [{sku: "KB-01", qty: 2}], total: 59.9, currency: "EUR"}',
    "unescaped quote": '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2}], "total": 59.9, "currency": "EUR", "note": "customer wrote "urgent" twice"}',
    "truncated output": '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2}, {"sku": "MS-',
    "NaN value": '{"order_id": "A-1001", "items": [{"sku": "KB-01", "qty": 2}], "total": NaN, "currency": "EUR"}',
}
