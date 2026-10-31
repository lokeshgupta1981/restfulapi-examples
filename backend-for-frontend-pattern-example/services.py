"""Three general-purpose downstream services of the bookstore.

They know nothing about web or mobile screens. Each one returns the full
resource, and each waits SIM_DELAY_MS to stand in for a database query.

Run one of them with uvicorn, for example:
    uvicorn services:orders_app --port 8001
"""
import asyncio

import jwt
from fastapi import FastAPI, Header, HTTPException

import settings


def require_token(authorization: str | None) -> dict:
    """Accept only a valid demo access token: 'Authorization: Bearer <jwt>'."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    try:
        return jwt.decode(authorization[7:], settings.TOKEN_SIGNING_KEY,
                          algorithms=["HS256"], audience="bookstore-api")
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid token: {e}")


async def simulated_work():
    await asyncio.sleep(settings.SIM_DELAY_MS / 1000)


# ---------------------------------------------------------------- orders
orders_app = FastAPI(title="orders-service")

ORDERS = {
    "1001": {
        "id": "1001", "customerId": "alice", "status": "SHIPPED",
        "createdAt": "2026-10-28T09:14:00Z", "currency": "EUR",
        "lines": [
            {"lineId": 1, "bookId": "b-42", "quantity": 1, "unitPrice": "39.90",
             "discount": "0.00", "taxRate": "0.07", "warehouse": "FRA-2"},
            {"lineId": 2, "bookId": "b-77", "quantity": 2, "unitPrice": "12.50",
             "discount": "2.50", "taxRate": "0.07", "warehouse": "FRA-2"},
        ],
        "subtotal": "62.40", "tax": "4.37", "shippingFee": "4.90", "total": "71.67",
        "billingAddress": {"name": "Alice Example", "street": "Hauptstr. 1",
                           "city": "Berlin", "postcode": "10115", "country": "DE"},
        "shippingAddress": {"name": "Alice Example", "street": "Hauptstr. 1",
                            "city": "Berlin", "postcode": "10115", "country": "DE"},
        "payment": {"method": "card", "brand": "visa", "last4": "4242",
                    "capturedAt": "2026-10-28T09:14:05Z"},
        "shipmentId": "s-9001",
        "audit": {"createdBy": "web-checkout", "updatedAt": "2026-10-29T16:02:11Z",
                  "version": 7},
    }
}


@orders_app.get("/orders/{order_id}")
async def get_order(order_id: str, authorization: str | None = Header(None)):
    claims = require_token(authorization)
    await simulated_work()
    order = ORDERS.get(order_id)
    if not order or order["customerId"] != claims["sub"]:
        raise HTTPException(404, "order not found")
    return order


# ---------------------------------------------------------------- catalog
catalog_app = FastAPI(title="catalog-service")

LONG_TEXT = ("A practical introduction for working developers, with examples "
             "for every chapter and exercises at the end. ") * 6

BOOKS = {
    "b-42": {"id": "b-42", "title": "RESTful Web APIs in Practice",
             "subtitle": "Design, build and run HTTP APIs",
             "authors": [{"name": "Jane Writer", "bio": LONG_TEXT[:240]}],
             "isbn13": "9780000000421", "publisher": "Example Press",
             "published": "2025-03-01", "pages": 412, "language": "en",
             "description": LONG_TEXT,
             "images": {"thumb": "https://img.example.com/b-42/120.jpg",
                        "medium": "https://img.example.com/b-42/480.jpg",
                        "large": "https://img.example.com/b-42/1200.jpg"},
             "dimensions": {"heightMm": 235, "widthMm": 191, "depthMm": 24},
             "rating": {"average": 4.6, "count": 318},
             "categories": ["Programming", "Web", "APIs"]},
    "b-77": {"id": "b-77", "title": "HTTP Pocket Reference",
             "subtitle": "Status codes, headers and caching",
             "authors": [{"name": "Sam Author", "bio": LONG_TEXT[:240]}],
             "isbn13": "9780000000773", "publisher": "Example Press",
             "published": "2024-11-15", "pages": 180, "language": "en",
             "description": LONG_TEXT,
             "images": {"thumb": "https://img.example.com/b-77/120.jpg",
                        "medium": "https://img.example.com/b-77/480.jpg",
                        "large": "https://img.example.com/b-77/1200.jpg"},
             "dimensions": {"heightMm": 178, "widthMm": 108, "depthMm": 12},
             "rating": {"average": 4.3, "count": 97},
             "categories": ["Programming", "Web"]},
}


@catalog_app.get("/books/{book_id}")
async def get_book(book_id: str):
    await simulated_work()
    if book_id not in BOOKS:
        raise HTTPException(404, "book not found")
    return BOOKS[book_id]


# ---------------------------------------------------------------- shipping
shipping_app = FastAPI(title="shipping-service")

SHIPMENTS = {
    "s-9001": {"id": "s-9001", "orderId": "1001", "carrier": "DHL",
               "trackingNumber": "00340434161234567890", "status": "IN_TRANSIT",
               "estimatedDelivery": "2026-11-02",
               "events": [
                   {"at": "2026-10-29T16:00:00Z", "where": "Frankfurt", "what": "Picked up"},
                   {"at": "2026-10-30T07:40:00Z", "where": "Leipzig hub", "what": "Sorted"},
                   {"at": "2026-10-31T05:10:00Z", "where": "Berlin depot", "what": "Arrived"},
               ]},
}


@shipping_app.get("/shipments/{shipment_id}")
async def get_shipment(shipment_id: str, authorization: str | None = Header(None)):
    require_token(authorization)
    await simulated_work()
    if shipment_id not in SHIPMENTS:
        raise HTTPException(404, "shipment not found")
    return SHIPMENTS[shipment_id]
