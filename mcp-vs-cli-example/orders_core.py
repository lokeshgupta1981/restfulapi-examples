"""Shared core of the order service. The CLI and the MCP server both call these functions."""
import random

STATUSES = ["open", "paid", "shipped", "cancelled"]
PRODUCTS = [
    ("KB-01", "Mechanical keyboard", 89.00),
    ("MS-02", "Wireless mouse", 29.50),
    ("HD-07", "USB-C headset", 64.90),
    ("MN-27", "27-inch monitor", 249.00),
    ("DK-03", "Laptop dock", 129.00),
    ("CB-10", "USB-C cable, 2 m", 12.90),
]
CITIES = [("Berlin", "DE"), ("Lyon", "FR"), ("Austin", "US"), ("Pune", "IN")]


def _make_orders():
    rnd = random.Random(42)
    orders = []
    for n in range(1, 41):
        items = []
        for sku, name, price in rnd.sample(PRODUCTS, rnd.randint(1, 3)):
            items.append({"sku": sku, "name": name, "quantity": rnd.randint(1, 3), "unit_price": price})
        city, country = rnd.choice(CITIES)
        orders.append({
            "id": f"ORD-{1000 + n}",
            "customer_id": f"C-{rnd.randint(1, 8)}",
            "status": rnd.choice(STATUSES),
            "created_at": f"2026-09-{rnd.randint(1, 30):02d}T{rnd.randint(8, 19):02d}:15:00Z",
            "currency": "EUR",
            "items": items,
            "total": round(sum(i["quantity"] * i["unit_price"] for i in items), 2),
            "shipping_address": {"street": f"{rnd.randint(1, 99)} Market Street", "city": city, "country": country},
            "notes": "",
        })
    return orders


ORDERS = _make_orders()


def list_orders(customer_id=None, status=None):
    return [o for o in ORDERS if (customer_id is None or o["customer_id"] == customer_id)
            and (status is None or o["status"] == status)]


def get_order(order_id):
    for o in ORDERS:
        if o["id"] == order_id:
            return o
    raise KeyError(f"order {order_id} not found")


def cancel_order(order_id, reason):
    order = get_order(order_id)
    if order["status"] in ("shipped", "cancelled"):
        raise ValueError(f"order {order_id} is {order['status']} and cannot be cancelled")
    order["status"] = "cancelled"
    order["notes"] = reason
    return order
